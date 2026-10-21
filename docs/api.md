# Command and Contract Reference

## Renderer

```text
scripts/render-skills.py --write
scripts/render-skills.py --check
```

`--write` deterministically rebuilds eleven managed worker Skill directories plus
`skills/kaola-project-runner/` from `templates/orchestrator/` (control plane; not a twelfth
platform), `skills/kaola-delegator/` from `templates/kaola-delegator/` (external
delegation Skill; not a twelfth platform), and the Grok Bot host bundle `hosts/grok-bot/`: `kaola-delegator.md` (the one
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
or unexpected file, Skill directory, or host bundle file. Python `__pycache__/`
directories and `*.pyc`/`*.pyo` files are runtime byproducts, not payload:
`--check`, `--verify-install`, and the host-bundle verifier ignore them the
same way the installer digest and copy do. Any other extra file is still
unexpected. Manifest values are JSON strings in a
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
is sent literally and a rejection is reported as a limitation. `acp_command_default`
and `acp_command_<w>` (for a named tier) are optional per-tier spawn commands (Issue #140; only
Devin declares them, as `devin acp --model <preset id>`): when the tier preset selects the model,
`kaola-acp.py` spawns that command instead of `acp_command`, while `--command`,
`KAOLA_ACP_COMMAND`, an explicit `--model`, or a preserved resume keep the base; an empty value, or
`acp_command_<w>` for an undeclared tier, is rejected. `acp_session_new_timeout` is an optional
number of seconds in (0, 600] the holder waits for the `session/new` answer in `start` and the
`preflight` probe (Issue #146; absent keeps 15 s; Codex declares `60` because live Codex
answered after ~18 s, and Droid declares `60` because live Droid answered after ~24 s,
Issue #352). The client start window (20 s) and the probe bound (60 s) grow by the
amount it exceeds 15 s, keeping the margins they had over the default wait; the holder reports
no answer in time as `acp-session-timeout`. Model-selection fields are
`default_model_name`/`default_model_id`/`default_model_parameters`/`default_model_effort`/`default_model_profile`,
optional `default_model_components`, `named_tiers`, and `fast_support`/`fast_summary` (Issue #188, components Issue #237). Only `default` is common;
`named_tiers` is the comma-separated list of the platform's own tier words (empty for none), and
each word `W` carries `<w>_model_name`/`<w>_model_id`/`<w>_model_parameters`/`<w>_model_effort`/`<w>_model_profile`
and may carry `<w>_model_components`
with `w` = `W` with `-` as `_` (name and id required; a profile may be empty and has no `|`,
Issue #190). Optional `default_model_roles` and `<w>_model_roles` are a comma-separated closed
vocabulary. The only value is `computer-use-only`. Absent or empty means no roles. An unknown,
empty, or repeated token rejects that catalog row at render and at `project`; it is never a
silent default. Profile prose is not a role (Issue #350). Profiles are selection guidance rendered only into Project Runner's
`references/worker-profiles.md`; they never change a preset or gate `start`. The words are unordered names, not a
ranking. They reach the generated Skill through the computed `PRESETS` (SKILL.md) and
`PRESET_LINES` (references/platform.md) blocks. They render as `ACP_COMMAND`, `ACP_QUIRKS`, and `ACP_LOGIN_REQUIRES_PTY`
template variables; `acp_login_requires_pty` only records whether login needs a native terminal —
login is a human act outside the Runner. `login_summary` and `permission_summary` (Issue #157)
are required prose keys rendered into the worker SKILL.md: the platform's own login fact, and the
permission mode `start` sets by default plus the `--permission-mode` override. The manifest key `default_transport` is removed
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
                         [--quarantine-stale-backups]
```

Platform IDs are `grok`, `claude-code`, `opencode`, `kimi-cli`, `cursor-cli`, `devin`, `codex`, `zcode`, `droid`, `dsh`, and `antigravity`.
Omit `--platform` for all eleven workers. `--platform` never selects the main Skill;
`kaola-project-runner` is not a platform ID. The orchestrator is installed for every `--runtime`
and `--skills-dir` destination unless `--no-orchestrator` is passed. Every selected destination is
preflighted before mutation; foreign paths are never replaced. Before any write an install also
runs this checkout's own `scripts/render-skills.py --check` and refuses with the
`./scripts/render-skills.py --write` remedy when the generated Skills do not match their
templates (Issue #215); an uninstall reads no payload bytes and is not gated. After the writes
the installer verifies every requested Skill at every requested destination (link targets for
`--method link`, tree digests for `--method copy`) and exits nonzero when one did not land — a
write failure is never reported complete. A `--platform` or `--no-orchestrator` request is
reported `scope: filtered` with the unselected siblings' states and `NOT a complete-root
install`; only an unfiltered request reports `scope: complete`. Those `verify:` lines and
`render-skills.py --verify-install` check Skill payloads only; neither is runtime or ACP
verification. A successful install then prints a footer: payloads verified, runtime/ACP
completion still owned by the executing agent, the canonical procedure
`docs/api.md#acp-layer-preparation-during-install`, and the platform selection to continue
with. The footer does not claim checks the script did not run. `--uninstall` prints no such
footer and does not start that procedure. Names this checkout no longer
generates but a receipt still owns are obsolete copies: the installer retires one only when no
other referrer remains and the copy's bytes still match the receipt, and preserves — with a
named owner-safe next action — a modified, co-owned, foreign, or unreceipted path.

### Installer backups and the quarantine

The installer's `.${name}.drift.$$`, `.${name}.old.$$`, and `.${name}.tmp.$$` siblings are
manageable artifacts, never Skills. A copy-mode `repair` and a `relink-drift` still keep the
previous copy for inspection, but it goes to the runner-owned quarantine instead of the Skill
discovery root. Each install also moves stale backup-shaped siblings in the roots it is about to
write into the same quarantine before it writes, and prints every move. The default quarantine is
`${XDG_STATE_HOME:-$HOME/.local/state}/kaola-project-runner/install-quarantine` (override with
`KAOLA_PROJECT_RUNNER_QUARANTINE`); one timestamped `run-*` directory holds the moved entries and
a `manifest.jsonl` whose rows record `schema`, `ts`, `original_path`, `quarantine_path`, `root`,
`skill`, and `reason`. Nothing is deleted: the previous bytes stay available under the quarantine
path. `./scripts/install-local.sh --quarantine-stale-backups --skills-dir ROOT` performs only
that recovery for an existing root (it installs no Skill), and a normal install performs the same
move. A stale backup is not an installed Skill, so it never causes the build-skew refusal and
never blocks `start` on its own; a `start` that finds one reports `stale_install_backups` (with
`stale_install_backup_count`, `stale_install_backup_roots`, and
`stale_install_backup_recovery`) so the operator can run the quarantine command.

### ACP layer preparation during install

This procedure is how every installation finishes, including a normal local install and a
Grok Bot bound-target install or update. A successful `install-local.sh` exit, a `verify:`
line, and `render-skills.py --verify-install` prove Skill payloads only. They are not runtime
or ACP readiness, and they are not permission to call the installation complete. `--uninstall`
is not this procedure. A bridge-only placement UAT is placement only.

Do this once per installation, on the bound execution target, in this order. Copying Skills
into more than one root does not repeat it.

1. Survey. Reuse `kaola-acp survey` (read-only; it runs no platform binary) together with the
   explicit install selection. Check each detected in-scope runtime once. `--runtime` selects
   the consuming Skill destination, not the only worker CLI to inspect. `--platform` narrows
   worker scope; with no `--platform`, cover every detected supported runtime. Required
   preparation covers installed runtimes: an absent CLI the selection did not explicitly
   request is outside that scope — report it skipped, not as an obligation to install
   everything. A runtime explicitly requested but missing is a distinct recovery item. An
   unresolved `unknown` is a missing fact to resolve, not guessed absence. Installing eleven
   Skill folders does not prove eleven CLIs are present. Do not install an absent CLI
   automatically.
2. Install or update the selected Skill payloads with `install-local.sh` and accept only its
   existing payload verification. A nonzero exit stops this procedure.
3. For each in-scope runtime the survey reports present, resolve the actual launch path and
   component versions from that platform's current manifest (`acp_command`,
   `acp_verified_versions`, `acp_wrapper_pin`, and the linked platform facts) and from native
   package or runtime evidence. Distinguish the CLI, a bundled harness, an independent
   adapter, a KPR bridge, and version overrides such as `CODEX_PATH`. Read verified versions
   from the manifest. Do not copy them into a second catalog and do not invent semver
   compatibility from numeric ordering. A newer version than the verified record stays
   unverified. Do not silently downgrade. A CLI version or ACP `agentInfo` string can name a
   different layer than the one that was loaded.
4. If a component is missing or older than its verified record, carry out preparation that
   existing authorization already covers, using that component's documented package or app
   mechanism. An inseparable ACP harness may require the containing CLI update (DSH). An
   independently pinned pair does not replace an unrelated global CLI (Codex). A KPR-owned
   bridge or adapter is refreshed by the Skill install in step 2. Do not select an unverified
   upstream latest. Do not ask again when existing authorization covers the update. A whole-app
   update that authorization does not cover, or an unsafe change to a shared live session, is
   a concrete pending action: print `HUMAN_DECISION_REQUIRED` and wait. Do not report success
   and do not restart shared live sessions. Preserve account, provider, and model settings.
   Do not log in or relogin. Do not fix the OpenCode Go route as part of this procedure.
5. Verify the component that is actually loaded. Reuse protocol evidence that still applies
   to that unchanged layer. If the layer changed or has no such evidence, use the existing
   bounded ACP path — `preflight`, `start`, `status`, and exact `stop` — on one disposable
   session if needed, via the [Runner entrypoint](#runner-entrypoint-kaola-tmuxsh). No
   obligatory model prompt, model-catalog gate, capability test, or recurring scan. A
   transport handshake does not prove model execution. DSH provider-route limits stay stated
   separately.

Then report one compact row per in-scope runtime in the same installation result. No new
state file, schema, or ledger. Each row is one line:

```text
acp: RUNTIME component=LAUNCH versions=OBSERVED verified=MANIFEST_RECORD action=ACTION readiness=READY_OR_REMAINING
```

`RUNTIME` is the platform id. `component` is the resolved launch path or command. `versions`
is what that launch actually loaded. `verified` is the manifest record those versions were
compared with, or `unverified`. `action` is what this installation did, including `none` and
`pending`. `readiness` is `ready` only when the required preparation has supporting evidence;
otherwise it is `not-ready:` plus the exact remaining action. Keep Skill payload success, ACP
preparation, and any known account or model execution limit in separate clauses. Call the
installation complete only when every required in-scope preparation has supporting evidence.
Otherwise report the completed subset and the concrete outstanding work. A guide link, a
recorded pin, or a proposed upgrade is not that result.

Report an absent unrequested runtime as `skipped: absent` — outside required preparation, not
a blocker for calling the installation complete. Report a runtime the selection explicitly
requested but found absent as `not-ready: absent` with the concrete recovery (install that
named CLI through its supported mechanism and rerun this selection). Report `unknown` as
`not-ready: unknown`, a different row from absent, with its concrete resolution: rerun the
existing survey in the correct bound-target launch environment (login shell, PATH, and any
manifest binary override) and resolve the missing fact before deciding absence. Prerequisites
that block a launch stay in the row: Node.js/npm before the Codex adapter, or
`KAOLA_ZCODE_ENTRY` and `KAOLA_ZCODE_NODE` for ZCode ([ZCode host](zcode-host.md)).

| Platform | Actual ACP layer and update boundary |
|---|---|
| `claude-code` | The vendored `claude-code-acp` Node bridge ships in the KPR Skill; reinstall that Skill to refresh the bridge, and check the Claude CLI version separately. |
| `codex` | The manifest npx command launches adapter `@agentclientprotocol/codex-acp` 2.0.1. The child CLI is the explicit absolute `CODEX_PATH` binary (requested Codex CLI 0.160.0). If `CODEX_PATH` is unset or empty, the Runner resolves `CODEX_BIN`, then `codex` on PATH, and supplies that absolute path to the adapter. An invalid explicit `CODEX_PATH` returns `codex-child-path` before spawn. Use `CODEX_PATH=/absolute/path/to/codex` to select one installed executable. No executable is installed by this resolution. The adapter's nested `@openai/codex` package does not select the child. `acp_verified_versions` records the launched child's package version in `cli=` and the adapter in `adapter=`, separate from `acp_requested_cli`. Node.js and npm/npx are prerequisites. |
| `cursor-cli` | `cursor-agent --yolo acp` is native to Cursor CLI; there is no separate adapter to update. |
| `devin` | `devin acp` is native to Devin CLI; there is no separate adapter to update. |
| `droid` | `droid exec --output-format acp` is native to Droid CLI; there is no separate adapter to update. |
| `dsh` | `dsh --profile acp`; inspect the loaded `dsh-acp-app` and `dsh-acp` packages as described below. |
| `grok` | `grok agent --always-approve stdio` is native to Grok CLI; there is no separate adapter to update. |
| `kimi-cli` | `kimi acp` is native to Kimi CLI; there is no separate adapter to update. |
| `opencode` | `opencode acp` is native to OpenCode CLI; there is no separate adapter to update. |
| `zcode` | The KPR Skill's `kaola-zcode-acp.py` adapter connects to the app's bundled ZCode app-server. Reinstall the Skill to refresh the adapter; update the ZCode app to update its app-server. |

#### DSH loaded ACP harness

The DSH ACP agent reports `deepseek-harness-acp/0.0.1` in `agentInfo` on multiple launcher
versions; that label does not identify the loaded harness build and cannot establish an upgrade
of the loaded packages. The harness packages are
`@deepseek-ai/dsh-acp-app` and `@deepseek-ai/dsh-acp`, resolved from the selected launcher's
installation. Check those packages and the launcher for the actual `DSH_BIN` (or `dsh` on `PATH`):

```bash
node -e 'const p=require("path"),f=require("fs");let d=p.dirname(process.argv[1]);for(const n of ["dsh","dsh-acp-app","dsh-acp"]){let m;for(let c=d;!m;c=p.dirname(c)){const x=p.join(c,"node_modules/@deepseek-ai",n,"package.json");if(f.existsSync(x))m=x;else if(c===p.dirname(c))break}if(!m){console.log(n,"not found");break}console.log(n,JSON.parse(f.readFileSync(m)).version,m);d=p.dirname(m)}' \
  "$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$(command -v "${DSH_BIN:-dsh}")")"
```

Under the route condition recorded in the DSH manifest, the verified package pair is
`0.2.1-rc.2` (ACP protocol 1). A scratch `initialize` on launcher `0.2.1-rc.2` reports `deepseek-harness-acp 0.0.1`, the same agent label a live `initialize` reported on 2026-10-16 under `0.2.0-rc.2` and under `0.1.7-rc.2`. DSH >= 0.2.1-rc.1 is required for DeepSeek 1017. Its launcher pins both harness packages to the same exact version,
so there is no standalone harness upgrade. Keep a matching installation. If the selected DSH
install is elsewhere, set `DSH_BIN` to that binary. If either harness package is missing or too
old, the recovery is to install/update the whole `@deepseek-ai/dsh` package, for example
`npm install -g @deepseek-ai/dsh@0.2.1-rc.2` with the npm prefix that installed it; apply the
authorization rule above before that whole-CLI action. For changed or unverified DSH layers, the
existing bounded check is `preflight`, `start` (the receipt's `transport.agent_info` confirms the
ACP handshake, not the package version), `status`, and exact `stop`; it needs no model turn. Report
any model, provider, or credential failure separately without changing those settings.

The local DSH adapter also handles an argument-free `/compact` ACP text prompt through the
same process-local overlay. Source support is confirmed in DSH `0.2.0-rc.2`:
`ctx.compaction.compactNow(agent, signal, commandId)`. This calls the native idle-session
operation. It retains the selected model and the native range, busy and save checks.
An open ACP prompt is refused. A native `null` result ends the command without a completion
signal. A save failure remains a failure, even if the native end event exists.

The adapter maps a successful return and its matching current-session `compaction/summary`
and `compaction/end` events to `compaction_update` with the native occurrence id. Its
`_meta["dsh/compaction"]` retains the bounded native receipt. This is a local adapter mapping,
not an upstream ACP notification. Ordinary prompts and steering keep their existing routes.
ACP cancellation stays available during this call. Disconnect cancels its request signal;
unknown effects require original-session reconciliation before retry. No profile or install
file is changed. Direct custom DSH commands bypass this overlay. Automatic compaction outside
this finite request still has no forwarded completion on the shipped ACP route. Use the
existing inquiry recovery there. Live compaction and post-compaction read/use on this new
route remain pending; model-free adapter tests do not establish them.

dsh pins the session's permission into its session log at creation: the
`permission/preset`, `sandbox/mode`, and `approval/policy` events a `session/new`
writes are the values `session/resume` restores, so the launch variable
`DSH_PERMISSION_MODE` a resume still carries can never change them. A
`start --resume`/`--continue` receipt therefore reports
`config_application.mode` as `{"applied": false, "requested_via": "env",
"value": <requested>, "source": <source>, "reason": "resumed-session-permission"}`
and, when the session log under `$DSH_HOME/sessions/` is readable, the
session's own recorded facts under `effective` (`preset`, `sandbox`,
`approval`, `session_log`, with `effective_via: "session-log"`). An unreadable
or absent log reports no `effective` — it is never guessed. A session born
confined stays confined across every resume; gaining a wider preset takes a
fresh session, which the Delegator host-restart guide states for the Host
restart path.

Droid's executable override is `DROID_BIN`. Its ACP command is the native
`droid exec --output-format acp`; no bridge or translator is used. Droid defaults to Auto Model
(`model=auto`) and full bypass (`autonomy_level=auto-high`). The supported
`--permission-mode` values are `bypassPermissions|low|medium|high|manual`; ACP maps them to
`auto-high|auto-low|auto-medium|auto-high|normal` through `acp_mode_config_id: autonomy_level`.
ACP model, reasoning-effort, and autonomy options use config IDs `model`, `reasoning_effort`, and
`autonomy_level`. Droid's default preset is Auto (`auto`); `--tier opus` is Opus 5.5 (`claude-opus-5-5`,
`reasoning_effort=high`) and `--tier core` is Kimi K3 (`kimi-k3`, `reasoning_effort=max`); it has no
separate Fast toggle.

`--runtime` selects a verified consuming-runtime destination: `codex` →
`${CODEX_HOME:-$HOME/.codex}/skills`, `claude-code` → `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills`,
`cursor` → `$HOME/.cursor/skills`, `devin` → `${DEVIN_CONFIG_DIR:-$HOME/.config/devin}/skills`,
`zcode` → `$HOME/.zcode/skills` (ZCode Host install; verified default discovery roots are the
workspace `.zcode/skills` and `.agents/skills`, which `--skills-dir` covers — see
[ZCode host](zcode-host.md)),
and (Issue #119, each measured as that CLI's Skill root) `grok-cli` → `$HOME/.grok/skills`,
`opencode` → `$HOME/.config/opencode/skills`, and `dsh` and `droid` (Issue #193) →
`$HOME/.agents/skills`; `kimi-cli` (Issue #159) → BOTH
`$HOME/.agents/skills` (the cross-tool root, shared with `dsh` and `droid`) and
`${KIMI_CODE_HOME:-$HOME/.kimi-code}/skills` (the Kimi-specific root, which moves with
`$KIMI_CODE_HOME`), each with its own receipt set; which platforms can run Project Runner as a Host,
and with which first line, is the `host_skill_entry` table in the main Skill's
`references/host-entry-matrix.md`.
Issue #193: Droid documents `~/.factory/skills` and `~/.agents/skills` as one user bucket in
which same-name Skills are invalid, so `--runtime droid` (install and `--uninstall`) also
withdraws the `droid` reference from the retired `$HOME/.factory/skills` under the uninstall
rules below: a Skill whose last referrer was `droid` is removed there, one another runtime still
refers to is kept with a duplicate-name warning, and a droid-only copy with edited bytes or a
same-name directory without a receipt refuses the run before any write. Other Skills there,
including personal ones and a `kaola-delegator` leftover, are untouched. A `~/.factory/skills`
that resolves to the shared root is skipped. Other runtimes keep their runtime-specific roots.
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
ledger and counts as referenced by every runtime mapped to that root when it was written
(`kimi-cli,dsh` for `$HOME/.agents/skills`, `droid` for the retired `$HOME/.factory/skills`),
so a guess never removes it. A pre-ledger receipt in the Kimi-specific root instead counts as
referenced by `kimi-cli` alone — its only installer — so a kimi-cli `--uninstall` withdraws the kimi-cli reference from BOTH roots
it owns: the shared root keeps its Skills while `dsh` still refers to them, and the
Kimi-specific root removes them because no referrer remains.

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
nonzero for a link another checkout made. Helper links are shared blocks, reported separately
from Skill alignment (Issue #215): after the Skills verify, each link's actual target, its
build digest, and its recorded referrers print as `helper: …`; a usable link still pointing at
another checkout's older build is kept and reported `helper not upgraded: …` with the owner-safe
transition (withdraw the other referrers first, or `kaola-locate.py register` for the locator),
never silently retargeted, deleted, or claimed upgraded.

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

## OpenCode managed native permissions

OpenCode V2 CLI 2.0.22 includes its ACP server (protocol 1). A fresh managed
`start` without an explicit mode, resume/continue or custom command selects an
`OPENCODE_CONFIG` file in that exact session's record directory containing only
`agents.build.permissions: [{action: "*", resource: "*", effect: "allow"}]`.
Model/provider/effort selections stay on the existing ACP path. Preflight does
not create or apply this file. `native_permission_policy.selected` reports the
launch selection, not an independent runtime policy readback.

The native file slot ranks above global config, and native build-agent rules
can outrank root rules. Runner therefore leaves existing configuration intact:
any supplied `OPENCODE_CONFIG`/`OPENCODE_CONFIG_CONTENT` (even empty), existing
native JSON/JSONC config or agent-source directory, or unreadable source defers
the default. Non-permission config also defers it; no parsing or merging occurs.
The receipt names the reason and, when readable, the source path. Deferred
launches still start normally with native policy. No shared configuration or
parent environment is changed. The selected file remains with the existing
session records after stop; it contains no model or account configuration.

Explicit `--permission-mode plan` maps to native ACP `mode=plan`, suppressing
the launch default. A later native plan selection also retains plan's edit
restriction because the allow rule is scoped to build. Unknown explicit mode
values are sent to the native option and retain its error; Runner does not
substitute build. Pending permissions still require an explicit Agent decision;
there is no automatic `permit` loop.

Actual 2.0.22 ACP QA exercised the file slot, external dummy `.env` read,
write/shell/reread, conflicting global/project policy, supplied native config,
and simultaneous independent sessions. Older V2 compatibility is source-only;
V1's `permission/bash/task` schema is distinct from V2's
`permissions/shell/subagent`. Native policy changes made after start, remote
well-known policy and arbitrary custom agents are not covered by this launch
adaptation's QA. No installed runtime upgrade is implied by the version facts.

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
(name, `present`: with a project and worker, ACP record presence through the shared
fixed/legacy-root resolver; `acp_holder_alive` separately reports holder PID liveness.
Without a worker, presence on the reachable tmux server only, not existence elsewhere and not ownership). A declared `--target` requires the registration receipt
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

## Outside-caller launch reconcile and resume wait (Issue #308)

The outside-caller launcher is `scripts/kaola-launchd-broker.py`. One session
has one job label, derived from the platform, the session, and the repo. Each
submit mints a new attempt directory, so a job left behind by an earlier
attempt is never owned by the attempt that is starting now.

```text
scripts/kaola-launchd-broker.py reconcile --platform ID --session NAME --repo GIT_ROOT
    [--record-dir DIR] [--run-base DIR] [--backend auto|launchd|systemd-user]
```

`reconcile` is the recovery route for that leftover:

- The job is absent. The receipt is `{result: reconciled, reaped: false}`. Nothing was unloaded.
- The job has exited and the session record has no live holder pid, agent pid, or agent process group. The broker boots the job out (one retry) and the receipt is `{result: reconciled, reaped: true}`. `submit` does this itself, so `start --resume` continues without a hand-run `launchctl` or `systemctl`.
- The job is still running, or the record still has a live holder or native agent. The broker does not unload it. The refusal reason is `job-occupied`. The text names the route: exact-stop the session through the Runner; when the one-shot has exited (`KeepAlive` is false; reconcile does not reap a job that is still running), run the `reconcile` command above, then retry `start --resume`. Do not run `launchctl` or `systemctl` by hand.
- The service manager cannot be read from this process. Reason `job-state-unknown`, nothing unloaded, and this is not evidence of a stale job: a Seatbelt caller sees `/bin/launchctl list` exit nonzero, so the receipt carries `os_state: "unknown"`, the read's `manager_rc`, a short `manager_stderr`, and `caller_confined: true` when `/bin/launchctl` exists but the read failed. The route is its own: do not retry `reconcile` or `start` from that same confined shell; run the `reconcile` command above once from an unconfined shell (`os_state: absent` with `reaped: false` means there was never a leftover), then retry `start` — `start --resume ID` only when this session's record carries an `acp_session_id`. The `job-state-unknown` row of `scripts/kaola-recovery-routes.py` carries the same four steps, including the `auto` start's degradation to direct (`launch_backend_fallback_reason: job-state-unknown`) and the full-access fresh Host start for a Host whose recorded preset is `workspace-write`.

`submit` keeps `launch-in-progress` for a job that is still running and does not kill it. `cleanup` still refuses a non-owned exited job with `job-not-owned` and does not unload it. That refusal also names `reconcile`.

`kaola-acp.py stop` runs `reconcile` after the stop, including a stop where the holder is already gone. `kaola-locate.py --intent resume` runs it when `--worker` is a known worker, `--session` is set, and `--project` resolves to a checkout top level. Both attach `broker_job` only when the job was reaped or the broker refused `job-occupied` or `job-state-unknown`. An absent job adds no field. A live job does not turn an otherwise good attestation into a refusal. A missing broker does not fail the stop.

Resume wait. The holder sends `session/resume` (or `session/load` when that is the capability the agent advertises) and waits:

- `KAOLA_RESUME_TIMEOUT`, when it is a finite number of seconds in (0, 600], wins. A non-numeric value, `nan`, or `inf` is ignored.
- Otherwise the wait is the platform `session/new` wait (manifest `acp_session_new_timeout`, default 15 seconds) plus `KAOLA_RESUME_TOKENS / 10000` seconds. A 960 000 token session adds 96 seconds. The total is capped at 600. The runner does not know the token count; the environment is the size hook. The explicit timeout wins over the token hint.
- The client passes that number to the holder as `--resume-timeout`. The broker does not forward `KAOLA_RESUME_*`.

The client keeps polling for 20 seconds after that wait (`RESUME_RECOVERY_GRACE`). On the outside-caller path the broker `--ready-timeout` is the resume wait plus the same grace, so the grace is inside the window that would otherwise kill the holder. A fresh session does not change the broker's 90 second default. A resume that becomes `ready` inside the wait returns immediately. A `session/resume` success that arrives after the wait, while the holder is still alive, clears `resume-failed`, sets the holder `ready`, and appends an event `resume_recovered`. The start receipt is then a ready session, not `resume-failed`. A success that arrives after the holder has been killed cannot be recorded. This wait is the load wait. The runner does not compact on resume, and it does not call `session/compact` while loading a session.
## Recovery routes (Issue #309)

No failure the runner reports is a dead end. Every refusal either carries a
recovery route (the next command or step) or tells the agent to route itself
and gives the context that choice needs. Error text that only names a problem
is a bug.

The table is [`scripts/kaola-recovery-routes.py`](../scripts/kaola-recovery-routes.py)
(`ROUTES`: each code maps to `route` or `self-route`). `stamp` attaches one
JSON field, `route` or `self_route`, on a failure envelope (`result` `refused`,
`error`, or `failed`, a follow `kind` of `error`, a skipped or incomplete
webhook scan that carries a string `reason`, a death wake with `sent` false,
and the same shape). It walks `holder_lost`, `delegator_death_wake`, and each
`wakes` entry before it decides the parent, so a successful start, stop, or
status receipt still stamps a failed nested wake. A non-empty `recovery` is
kept and is itself the route. Success results are left alone.
Correlation-index gap strings stay strings, so a stored index stays
compatible; when that code is the receipt `reason` or `error.code`, the
printed envelope carries the field.

The CLI, launch broker, locator, dispatch entry, installer, and Grok Bot
verifier attach the field on the next process. A direct holder-socket reply
is not stamped. The agent path is the CLI. Issue #320 is the holder-side
exception: when the holder cannot spawn the deliver child, it writes a
`failed` receipt through the webhook receipt writer, which stamps
`error` `spawn-failed` before the row is stored. `status.last_receipt`
returns that row. The holder also copies the deliver child's stderr into
its event log. A running holder does neither until it restarts.
A webhook delivery failure splits that route by HTTP class and by whether the
row is final. The split is in the delegator-webhook receipt section below.

A Host that cannot be resumed (timeout, `resume-failed`, `holder-lost`, an
unowned exited launchd job) is exact-stopped, attested, then `start --resume`.
If resume still fails, start a fresh Host and hand it the summary from
`status`, `capture --lines 200`, `list --repo --include-dead`, and
`delegator view`. The new Host re-adopts live seats from that list. This build
does not auto-reap the leftover job. The Delegator procedure is
`templates/kaola-delegator/references/host-restart.md`.

## Dispatch and collect (`kaola-dispatch.py`)

The orchestrator Skill ships one entry, `scripts/kaola-dispatch.py`, for an
adopted research, QA, or report plan. `project` prints a compact capability
summary taken from the profile text of presets that are authorized and marked
present, plus the eligible candidates' exact preset ids, Class, catalog
profile, `roles` (a sorted list, empty when the preset has none), selection parameters, and structured restrictions. `roles` is a catalog fact, not a grant. `execute` admits
that plan through each platform's existing `runtime-tmux.sh` and writes a
correlation index (`correlation_only`); a `--no-wait` admission is `in-flight`,
not a result. `collect` later correlates one status and, for a completed
turn, one capture, without waiting out a slower sibling. `collect` resolves
each platform Runner through `--skills-root`, the dispatch Skill's sibling
Runner root, then the checkout `skills/` directory; the chosen path and source
are recorded in `evidence.runner`. A missing Runner is `unknown` /
`runner-missing` with `runner_missing_attempts` and `runner_missing_limit` (3);
later collects retry it, and at the bound the row stays refused with its
recovery route until a collect resolves a Runner. A Runner that reports
`no-session` is `unknown` / `session-gone`. `snapshot` writes
the path given by `--out` (the Host carrier is
`.kaola/heartbeat-prompt.json`) so `body` is a string that parses as one JSON
object. The wrapper adds no schema key. `snapshot` refuses an `--out` that already holds
lifecycle state (`state-managed`). The index is not a mission ledger, and the entry does not choose a
plan, grant a seat, accept a result, or stop a session. Detail:
`templates/orchestrator/references/dispatch-collect.md`.

`scope` is `research`, `qa`, `report` or `implementation`; only `implementation` admits
`mutation: true`, and `execute` still claims nothing, creates no worktree and calls no forge.
An item sends its own `prompt`, or the plan's `core` (with `core_revision`) plus the item's
`worker_scope` joined by one blank line; giving both, or a core without its revision, is
`invalid-input`. The row's `prompt_source` records `kind` (`full` or `core+scope`),
`core_revision`, and the `sha256:` of core, scope and sent prompt. `execute --state FILE`
reads lifecycle state (holds are also read when `--authorization` is the v2 state file): a hold whose `preset` or `presets` names the item's preset makes a new
item `not-run` / `on-hold` (with `holds`) before any Runner call, and each admitted,
returned or unknown item with a `task_id` is added to that task's `dispatch` by writer
`tool:execute` without raising `host_revision` (`task_links` in the receipt; an unknown task
is an item `evidence.task_note`). A `collect` result carries `excerpt` (480 characters),
`excerpt_truncated`, `reply_chars`, `stop_reason`, `cursor`, `turn`
(`holder_instance_id`, `prompt_fingerprint`), `locator` (platform, session, the Runner
`capture` argv with `--since <dispatch cursor> --full --inline`, `event_log_path`), `output`
(`declared`, `kind`, `checked`; `kind` is `file` for a path-like string or `{"path": ...}`,
with `path` and `present`; `capture` for the reply itself, `present` from the reply text;
`remote` for a URL and `description` for text with spaces, neither checked; an explicit
`{"kind": ...}` wins) and `gaps` (`reply-text-absent`, `capture-truncated`, and
`output-absent` for an absent file only). A new return of an item whose acceptance was decided
resets it to `pending` and keeps the earlier value as `prior_acceptance`. `execute`, `collect`
and the `update --index` mirror write the index under one exclusive file lock, re-read it and
merge by item and field: a field this writer changed since its own read is its own, every
other field and every row another writer added stay as on disk.

Plan items may carry `task_id`, `output`, `requires` (`{"class": ..., "presets": [...]}`, a
requirement the Host stated for that item), and `issue` (a positive integer, or a decimal
string of one). `task_id`, `output`, `requires`, and a normalized `issue` are copied onto
the index row. `issue` does not admit or refuse the item. An
unmet `requires` is `not-run` / `requirement-unmet` before any Runner call; an item without
one is not compared. The index records `dispatcher` (the caller's `KAOLA_ACP_DISPATCHER`)
apart from each row's `notify_target` (the start receipt's `heartbeat_host`).

### Lifecycle state (`kaola-dispatch.py state`, Issue #255)

`state` maintains `<project>/.kaola/heartbeat-prompt.json` at schema
`kaola-heartbeat-prompt/2`: a structured `state` (`project`, `authorization`, `sideagent`,
`recovery`, `unverified`, keyed `tasks`/`holds`/`alerts`/`decisions`), a file `revision`, an optional `carrier`, and a generated `body` that is the
projected Host view. Old readers keep receiving a string `body`. Subcommands:

- `init`, `update`, `retire` write under a directory lock with `--writer host|sideagent` and
  `--source`. Any other writer is `writer-refused`. A record update is a JSON merge patch with
  `--expect-rev`; a stale revision exits 3 with `current` and `unapplied`. Section updates
  use `--expect-revision`; `project`, `authorization`, and `sideagent` are Host-only, except
  that the bound Sideagent may record its own `holder_instance_id` once. A Sideagent change to
  a Host-owned task field or `verdict` needs `--host-turn` and stays under `attention` in the
  Host view until the Host writes that task. A caller other than the bound Sideagent session
  and holder is `binding-superseded` or `sideagent-unbound`; the bound Sideagent writing as
  `host` is `writer-mismatch`. `retire` needs `--evidence` and a done or cancelled task, a
  settled decision, or any hold or alert. The record leaves the file. An update
  with its old revision is `record-retired`; a new sourced record uses the normal
  creation path. No settled tombstone is stored.
  `retire --kind decisions --id ID --absent --evidence E [--outcome R]` is Host-only, and only
  for a decision id with no current row (an owner closure that was never written as a row).
  The result is a receipt `{kind, id, outcome, absent_at_retire: true, evidence, at, host_revision}`
  and nothing else: no decision row, stone, or tombstone is stored. `host_revision` rises as on
  any Host business write, so the caller can cite that revision. `--absent` when `decisions/ID`
  is current is refused and names the normal retire. Without `--absent`, an absent id stays
  `record-missing` and the file is unchanged. A sideagent or any other writer is refused.
  Holds, alerts, and tasks take no `--absent`. A node checkpoint may still apply
  `retired:decisions/ID` when that row is absent. A
  task's `dispatch` items must be closed in `--index`, and every seat it names (`assignments`,
  `sessions`, `session`, including migrated ones with no index match) must show its session
  `stopped` in `--live` under the holder the task recorded. A string that is not a session
  name, such as a migrated note, stays on the task and is not a seat, so it does not require
  `--live`. A session name uses the recorded holder (`holder_instance_id` on an
  assignment, on a `sessions` object, or beside the task's own `session`); a missing row, a
  live or stopped row of a different holder, or two different recorded holders for one seat
  is not proof of stop, and `check --live` reports it as `done-seat-open`. `retire --handoff
  TASK` instead moves the dispatch refs, `sessions` and `assignments` (each object marked
  `handed_from`, keeping its holder and evidence; the task's own `session` becomes such a
  `sessions` object) to another current task, which then owns their stop.
  The command result names `handed_to`, `seats` and `dispatch`; the file stores
  no settled retirement row. A task in `review` without
  a verdict is under `attention` with a `content` digest, so each new result is a new wake; a
  task at `closeout` or `done` without an `accepted`, `partial` or `cancelled` verdict stays
  under `attention` as `verdict-missing`. Each write records `writer`; a `host` write from a
  caller whose own record names no role reads `host:<session> (role unverified)`, because the
  writer flag is a trace, not an identity proof. An accepted task also needs `--cite`
  with a required path. A commit is optional. When a commit is present,
  `git cat-file -e commit:path` must succeed. When a commit is absent, the path
  must be a file in the repository. Holds, alerts, cancellations, and relays
  still retire with `--evidence`. The command result carries the cite.
  Legacy retirement rows remain only while they name unresolved seats or dispatch. On migration a v1
  `pending` key with no v1 meaning is not copied and never acts as a v2 field of the same name.
- Each Host business write raises the file's `host_revision` and stamps the record (or
  section source) with it; a retirement returns that revision but stores no stone; tool and Sideagent writes do not raise it and stamp
  the caller's holder as `writer_holder`. Task `dispositions` maps item ids to `accepted`,
  `repair`, `cancelled`, `superseded` or `handed-off` (Host-owned); `update --kind tasks
  --index I` mirrors them onto the index `acceptance` with `acceptance_source`, and after a
  task `verdict` an item of that task with no disposition becomes `undecided` with an
  `acceptance_note`. The mirror result is `index_mirror`; a mirror error does not fail the
  state write. `retire --index I` uses the original task verdict to settle
  matching terminal rows. In-flight and unknown rows stay unresolved. `check`
  recognizes settled index acceptance without a retired registry.
- `checkpoint --writer sideagent --batch B --through-host-revision R --entries JSON
  [--events JSON]` (`--events` is accepted for older carriers) is written by a node-mode Sideagent (`sideagent.mode: "node"`) from inside
  its own session. Each entry names an `input` (a Host change id `host:<kind>/<id>@<rev>`,
  `host:section/<name>@<rev>`, or a worker event id) and
  either `applied` (current records this node's holder wrote, or
  `retired:<kind>/<id>` for a removed input record, without a stored stone) or
  `retained` (a current record with `next`, `owner` or `wait`, or a Host `section/<name>`).
  A Host decision row is `retained`, or `retired:decisions/<id>` when the row is gone, never `applied`.
  An unchanged current Host-owned record (`writer` is `host` or begins `host:`) that still
  names `owner`, `next` or `wait` at the selected `@rev` settles as retained whichever verb the
  node used. It is not returned and does not open `maintenance-returned`. A wrong verb on a
  present, owned, unchanged row is not "not applied". A vanished row, a later rewrite, a record
  with no `owner`, `next` or `wait`, a record a node wrote, and an input outside the selected
  batch stay on the existing returned, superseded, and already-settled paths.
  The checkpoint lands in `maintenance.last_checkpoint`; `last_verified` moves only when every
  selected input settled; an entry for a batch change the Host rewrote after `R` is listed
  under `superseded`, not returned, since the rewrite is the next batch's input; `acked_host_revision` never passes an unsettled change or one still
  open in the `maintenance-returned` alert, which receives each unsettled input once. A
  caller that is not the session's current node holder is `binding-superseded`; no caller
  identity is `node-identity-required`.
- `update --kind alerts --id ID --expect-rev N --evidence checkpoint:B --set
  '{"inputs":{"<input>":null}}'` removes one handled returned input (Issue #287). The tool
  accepts it only when the recorded checkpoint `B` settled that exact input, or is verified,
  reaches the `batch:` input's `host_revision_through`, and no returned Host change at or below
  that revision stays open. A recovery-only checkpoint therefore proves no unsent business range.
  A stop duty (`stop-unconfirmed`, `old-node-live`) ends only by its exact stop. An absent id
  refuses `input-missing`, an unproven removal `input-unproven`, a stale revision `conflict`;
  each changes nothing and names the exact command. Other inputs and newer duties stay;
  evidence references that only the removed input named leave with it, and an emptied
  `maintenance-returned` alert leaves the file. A checkpoint settles a returned input only
  when its batch carried it, never through `--events`, and keeps an uncarried input's
  original facts. A Host recovery request's batch also carries Host changes still pending
  past `handled_host_revision`, including a failed batch's range.
- An obsolete pre-v0.9.12 `maintenance-returned` input can leave without a node checkpoint
  (Issue #327). The same `update` removes one input when `--evidence` is an original reference
  the tool checks, and the input is one of three shapes: `batch:<rev>` (the unsent range through
  that host revision), `host:tasks/<id>@<rev>`, or a task id whose `why` is `not-in-batch`.
  `retired:tasks/<id>` proves that task row is gone, and for a `batch:<rev>` input that no current
  task, hold, alert, decision, or retirement stone still carries a host revision at or below the
  range. `closed:issue/N` with `--index` proves this project's `kaola-dispatch-index/1` has an item
  for issue N whose status is `returned`, `failed`, or `not-run` (no GitHub call); a task the input
  names must be that item's task and must not still be the current row at the input's revision.
  `stopped:holder/HOLDER` with `--live` proves that holder is `stopped` in this repo's
  `kaola-acp-list/1` rows and is not the bound node, and that the input is not still the current
  change. `superseded:REV` proves REV is a later current host revision that replaced the input:
  for one task, that task's current `host_revision`; for a batch range, the file's current host
  revision or a current record's, with no ready-queue row left at or below the range. A stop duty,
  a `recovery#` input, a `batch:<id>` that is not a revision, and any other shape still need the
  checkpoint proof. Evidence that does not check out refuses `input-unproven` and writes nothing.
  This removal does not raise `host_revision`, so it adds no queue input, no wake, and no node
  traffic. The alert leaves the file only when no input remains.
- A verified checkpoint also drops a returned input whose `host_revision_through` is at or
  below that checkpoint's `host_revision.through` (coverage, Issue #310). A `batch:` input
  stays while another returned `host:` change at or below that revision is still open.
  `recovery#` and any other non-batch input clear on that coverage with no open-change guard.
  A verified checkpoint that settled `recovery#N` removes that exact input even when its
  `host_revision_through` is above the checkpoint range (satisfaction). A later recovery
  sequence does not satisfy an older one. An input with no `host_revision_through` that this
  checkpoint did not settle stays. Stop duties stay until the exact stop. A partial checkpoint
  does not coverage-clear. The holder copies only the recovery inputs that remain into the
  next batch's `recovery_alerts`. A later failure record does not put a covered input back
  (`verified-past-revision`; a failure whose id is in `settled` stays
  `scoped-checkpoint-already-settled`). A `recovery#` this checkpoint did not
  settle, recorded at that checkpoint's own revision, is still written: the
  range has not moved past it. A new returned row records `host_revision_through`
  as the input's `@rev` when the id is `host:…@rev`, otherwise the batch `through`. An
  input this batch did not carry keeps its original facts, including a missing revision.
- A partial checkpoint record includes `missing_sources`: each unsettled input id mapped to
  `recovery-sources-empty`, `not-in-batch`, `unaccounted`, or `other`. `returned_to_host`
  keeps the detailed reason. The returned alert input's `why` is that vocabulary term; when
  the detailed reason differs, it is that input's `evidence` string. The carrier's
  `checkpoint-partial` row keeps `why` `checkpoint-partial` and carries the same
  `missing_sources` map. The holder's `sideagent_node_settled` event copies the map, and
  the Host wake names each `input why`. An older checkpoint with only `returned_to_host`
  still names its sources from those reasons.
- At `state init` and at holder startup, a carrier whose holder record advertises
  `sideagent-node/1` binds node mode from an eligible Worker: the Delegator file's
  `authorization.sideagent.preset` when that id is eligible, otherwise the first granted
  Worker by id. A `computer-use-only` role and exclusions are skipped. An existing binding
  is not replaced, and resume keeps it. The bind does not raise `host_revision` and is not
  itself a node input. When no eligible preset exists or the runner cannot be built,
  `sideagent` stays unset and `state check` reports `sideagent-default-unbound` with the
  `state ensure-sideagent` command. The next Host boundary retries.
- With node mode, worker events are not node inputs: they reach the Host at its next idle
  boundary as without a binding. A Host holder advertising `sideagent-node/1` starts one fresh
  node per batch of Host business changes past `handled_host_revision`, selected only while the
  Host turn is not active (at a Host turn end or the idle tick), from `sideagent.recipe` (`runner`, an absolute file, and `argv` starting with `start`, or with the bound platform then `start` for the checkout
  `kaola-tmux.sh`, bound
  `--session` and `--repo`, `--role sideagent`, never `--continue`/`--resume`; an optional absolute `state_tool`), sends it
  one batch prompt naming the Host revision range, the exact `state checkpoint` command and
  state file, and the node's role limits (source pointers only, no restated result, no
  dispatch, session control, task authoring or Host decision). At that node's turn end it
  settles the batch from the node's checkpoint: verified, the node's turn end reaches the Host
  once (`verified; Host attention changed`) only when an attention item is a record that node
  wrote and the Host view's attention fingerprint differs both from what the Host last saw and
  from the batch's start, and is quiet otherwise (the Host's own writes during the batch
  are not news to it). A `maintenance-returned` alert whose inputs are all unchanged current
  Host-owned records with `owner`, `next` or `wait` is not attention news and does not wake the
  Host; a partial checkpoint is quiet the same way when every returned input is that class.
  Delegator dedup of standing Host maintenance is unchanged. A partial that returns anything
  else, a missing checkpoint, or a checkpoint `through` below the sent range reaches the Host
  once naming the unhandled range, and that range is not sent again. A batch the node does not
  admit, a failed start and a lost node are staged for the Host once as a `node` item naming
  the unhandled range; the first two start no further node until the binding changes. The
  carrier then exact-stops the node. Host business changes are node inputs only under a node
  binding (`mode` `node`, `state` `active`); with no binding, or one in another mode or state,
  a Host write owes no batch and records no failure (Issue #324). A node binding whose recipe
  is refused records one `binding-or-recipe-unavailable` input and wakes the Host once; while
  that input stays in `maintenance-returned`, later Host writes add no failure and no wake.
  The Host's bounded request selects every change past the handled revision, and a repaired
  binding sends the changes after the failed one to a fresh node. A typed recovery input
  without a usable binding still records its one failure per sequence.
  The bound runtime is not a pin (Issue #324). When its Runner file is missing, its start
  fails, or its node does not admit a batch, the carrier moves the node to the next runtime
  instead of failing: only Worker presets that `kaola-dispatch.py project` finds
  eligible now (an explicit Worker grant, exclusions, holds, Delegator ceiling, availability not `absent`),
  sorted by preset id, skipping every runtime already tried for this
  binding, and skipping every candidate whose `roles` include `computer-use-only` (Issue #350).
  That skip is not an authorization change: grants, exclusions, holds, and availability stay as they are,
  and `project` still lists the preset for an explicit dispatch. No remaining Worker preset means the chain fails once and returns; it does not try an ungranted preset and it does not add a wake reason. The fallback start is the same Runner start from the sibling installed Skill
  (`<root>/<platform>-kaola-project-runner/scripts/<runner>`, or the checkout entrypoint with
  that platform first), the bound `--session`, this `--repo`, `--role sideagent` and the
  preset's `--tier`; the bound `--model`/`--effort` are dropped. A preset whose Runner is not
  on this machine is skipped. Each move is one `sideagent_node_fallback` event (`from`,
  `to`, `chain`, `tried`) and starts no Host turn. The chosen runtime serves later batches
  until the Host changes the binding or the holder restarts. Only an exhausted chain
  (`exhausted: true`) records the failure above, once, and starts nothing further. A stop is confirmed when the node's holder process is
  gone, not by its `stopped` record; while it still runs (`sideagent_node_stop_unconfirmed`)
  no node starts, and once it is gone (`sideagent_node_stop_confirmed_late`) the next Host
  change starts a fresh node. A holder whose stop reply cannot be delivered still exits.
  The holder and state tool use the same current-input selector. A retirement with no
  selectable input starts or sends no node and advances no checkpoint revision. If an
  owned node finishes startup after its input disappears, the carrier waits for the Host
  turn to end, then exact-stops that unassigned node. An assigned batch keeps its original
  range and checkpoint. Older holder bundles without this selector keep revision-only selection.
  A node is the carrier's own session, not a dispatched worker: a Host `stop` in every mode
  (default, `--force`, `--preserve-dispatched-workers`) starts no new node, waits up to 8 s
  for a node start in flight, and exact-stops the running node, found by its record's
  `dispatcher` when the start is still running.
- `view --role host|sideagent|delegator` reads only. The Host view adds `host_revision`,
  `dispositions` and a `maintenance` brief; the Sideagent view adds `host_revision` and
  `pending_host_changes`; the Delegator view adds `maintenance`. The Delegator view lists the `AGENTS.md`
  user-requirements region, holds, alerts, pending decisions, `unverified`, then doing, todo,
  and outcomes. Unknown content is `unknown` locators. It is not view text.
  Host view derives capability from current grants, explicit Worker grants, exclusions, holds
  and actual availability. Class definitions/defaults come from matched catalog/templates.
  Grouped grants own one count, choice set and switch permission; compatibility rows are generated.
  `count` on a grouped grant is the shared pool. `extra_seats` maps a member preset id to a positive
  extra seat count for that tier only. The per-runtime total is the pool plus those extras. A preset
  may appear once in `elite_grants` and once in `expert_task_grants`; that overlap is the Expert
  permission, not a second seat. Two rows in one list stay duplicates.
  Stored authorization contains no Class copies, capability list, aggregate cap or second switch/pause list.
  Legacy ambiguity blocks migration with original-source owner recovery; active duties remain.
  `delivery-open` content is the task `goal`, `next`, and verdict value.
  For `mode: node`, `sideagent_maintenance` says `a node is running` only when the
  record for this canonical repo digest is `ready`, its `holder_pid` is alive, its
  `repo` matches this state file, and its `dispatcher` matches this file's Host
  carrier (`platform`, `session`, `holder_instance_id`, and `repo`). The record
  root is `KAOLA_ACP_RECORD_ROOT`, else `XDG_RUNTIME_DIR`, else the process
  temporary directory, then `kaola-<uid>`. A missing record or a dead pid says no
  node is running. An unreadable record says liveness was not read. The sentence
  reports the view. Transport stays on the existing start, send, and stop commands.
- `check [--index] [--live] [--repo]` reports problems without writing.
- `timer --repo --target --entry [--body|--body-file]` compares a supplied native timer body
  with the entry line plus the fixed locator sentence. Exit 1 on `mismatch`. No body returns
  `unavailable` and exit 0. That is not a mismatch. It does not block an owner stop.
- `migrate` is a read-only plan unless `--write`; see
  [state-format migration](conventions.md#state-format-updates-and-migration).
  On schema `/2`, the report includes `removed`. Each name is a locator.
  A current record written before record revisions carries no usable `rev`, so
  `update`, the returned-input settle, and `retire` of a non-alert or
  unresolved row refuse it `record-versionless` and name this migration as the
  repair; the write assigns `rev 1` (`<kind>.<id>.rev assigned 1` in `removed`),
  after which the normal command and all its gates apply unchanged. `check`
  emits the read-only plan as such a row's `command`. One narrow exception
  (#395): an `alerts` row whose `inputs` is an empty object (resolved) retires
  directly with explicit `--expect-rev 0` and non-empty `--evidence`; `check`
  emits that direct command instead, and the receipt keeps the evidence.
- `delegator view|update|migrate --file .kaola/delegator-heartbeat.json` is the Delegator file tool.
  `project.user_language` is an optional string. It is the language for Delegator replies to the user.
  A missing key stores no language. The tool does not choose one.
  Plan migration before `--write`. Blocked paths name the allowed form and
  recovery; refusal leaves the bytes unchanged. Updates write the normalized
  closed form. Pending text in legacy bags must move to typed watch duties
  before those bags can leave. Views omit historical bags. One authorization
  shape check serves writes, migration, and the dispatch ceiling. `delegator update` accepts one
  grouped `elite_grants` row with `extra_seats` plus that preset once in `expert_task_grants`. A malformed
  grant with known preset ids refuses those ids; malformed pool authorization
  refuses that class. A `worker_grants` row names `preset_ids` (Worker preset ids) plus `count` (a nonnegative integer or the literal `unlimited`), optional `expires`, and `state` (`granted`, `paused`, or `revoked`; omitted means granted). Every Worker grant is a per-preset row; granting all presets is written as one row per preset, and there is no `scope` or other shortcut form — a `scope` field on a row is refused with the per-preset form named. A stored `all-worker-presets` row is expanded once by `delegator migrate` into one row per covered, non-excluded Worker preset, carrying the row's count, state, and expiry; after that the old form is refused. The Host `authorization.grants` mirror carries the same per-preset count: a nonnegative integer or the literal `unlimited`. A missing, null, or malformed `count` refuses that row and is not `unlimited`. A named row with a bad count refuses those ids; a row whose ids cannot be read or an unreadable `worker_grants` value refuses the Worker class. The same preset twice refuses the list. A Worker preset also named on an Elite or Expert row refuses. `unlimited` does not authorize Elite or Expert and does not override an exclusion. The closed form sorts `preset_ids`. A well-formed legacy `worker_pool` is removed on migration and is not copied into `worker_grants`. The Delegator view lists `authorization.worker_grants` (coverage `named-presets`, count as the integer or the word `unlimited`, expiry) and `worker_grant_statement`. With no grants that statement is `No Worker grants. There are no Workers until the owner grants some.` Dispatch `worker_ids` come only from current `worker_grants`. An unauthorized Worker preset is `no-worker-grant`; an expired one is `worker-grant-expired`. A numeric count is enforced. Only an explicit `unlimited` grant that covers that preset skips the count check. Legacy aggregate limits require original owner reconciliation. Owner conditions remain literal until mapped
  from original authority. An untyped old file produces an actionable
  migration observation from `execute`; legacy Host authorization continues.
  `adopted` needs a string `evidence` or `locator` that names the Host record or path. `sent` does not.
- An accepted task `--cite` needs a retrievable path. A commit is optional. When a commit is present,
  `git cat-file -e commit:path` must succeed. Holds, alerts, cancellations, and relays use `--evidence` only.

The Host view is bounded at 64 KiB (`host-view-too-large`). The whole file is bounded at
1 MiB when `carrier.capability` is `heartbeat-state/2`, else at the 64 KiB legacy reader
limit (`carrier-limit`). `state migrate` without `--live` uses the 1 MiB bound: missing
live rows are not an old holder. `carrier-limit` applies when `--live` is supplied and that
holder does not advertise `heartbeat-state/2`. The tool refuses rather than truncating a record.

#### Backstop sweep (`kaola-dispatch.py sweep`, Issue #348)

`sweep --repo ROOT (--dry-run | --apply | --record-empty) [--file STATE] [--batch B]
[--skills-root DIR] [--live FILE]` removes residues the main flow missed. `--file` defaults to
`<repo>/.kaola/heartbeat-prompt.json`. Exactly one mode is required. Output is one
`kaola-sweep/1` receipt: `{result: planned|nothing|swept|recorded-empty|candidates|refused,
mode, key, candidates, kept, removed, skipped, report, head, accepted_revision, forge, acp,
timed_out, recovery?}`. `report` is the R1-R3 report-only list (always present, `[]` when
none; `[]` on a node `--batch` receipt, which re-verifies only planned ids). `acp` is `"known"`
or `"unavailable"` (#353: an unanswered list is
`acp-unknown` skips, never removal); `timed_out` names the child tools whose calls timed out
(`git`, `gh`, `acp`; always present, `[]` when none).
`accepted_revision` is the verified caller record's value on apply/record-empty, null
otherwise. `key` is the
first 16 hex of the sha256 of the sorted candidate ids (`""` when none). Candidate ids are
stable: `session:<platform>/<session>@<holder>`, `worktree:<resolved path>@<HEAD sha>`,
`worktree-prune:<resolved path>`, `branch:workflow/issue-N@<sha>`,
`stale-file:<resolved path>@<int mtime>`.

The candidate set is a closed rule set; everything else is never touched:

- **S1** a `list --include-dead` row (one global list per scan since #353, partitioned by
  repo) whose repo is ROOT, `name_role` `worker`,
  issue parsed from the session name, issue CLOSED, `identity` `verified` - never a
  `session_role` host/sideagent row, the bound Sideagent session, or the caller's own session;
  a dead row is not a candidate. `status` is then read: `turn-active`, `permission-pending`
  and `identity-mismatch` keep the session. `old_version: true` marks a `stale` row or one whose
  `reported_drift` carries the skill-pin drift value (informational). Apply exact-stops with
  `--expected-holder-instance-id` and re-lists; a holder still live is kept `stop-unconfirmed`.
- **W1** a linked worktree (never the main worktree) bound to issue N by branch
  `refs/heads/workflow/issue-N` or basename `issue-N`, issue CLOSED, inside the resolved
  project root, unlocked, clean (`git status --porcelain` empty, including untracked), merged
  (HEAD an ancestor of `refs/remotes/origin/HEAD`'s target, else `origin/main`, or equal to
  the merged PR's `headRefOid`; no fetch), with no live verified session for issue N in ROOT
  or in the worktree itself. Keep reasons: `outside-project`, `locked`, `uncommitted-changes`,
  `unmerged-or-unpushed`, `live-session`. A worktree whose only live session is itself an S1
  candidate is still a candidate (the stop goes first). Every check is re-verified immediately
  before `git worktree remove <path>` (no `--force`); the branch is left for B1.
- **W1 cwd guard (#369/#389).** The removal goes through the same guarded wrapper as
  `worktree-remove` (below). It reads the cwd of the wrapper's own process chain (the caller's
  tool shell, agent CLI and holder) and of every live session tree of ROOT and its worktrees,
  from `/proc/<pid>/cwd` or `lsof -a -d cwd` (one call per pid list; a `(deleted)` suffix is
  `cwd_deleted`). A live cwd inside the target, a recorded `tool_cwd.last_known` inside it
  (`source: recorded`, even with no process), and an unreadable probe are recoverable under
  #389: the sweep proceeds with a typed warning (`occupied-cwd-recoverable` or
  `cwd-unverifiable`) and the holder recreates a vanished path. The receipt's top-level
  `warnings[]` carries `{code, path, detail, recovery}`; a candidate also carries its own
  `warnings[]`. Only a live process cwd plus uncommitted changes is a cwd hard block; the
  existing `uncommitted-changes` keep independently protects any dirty worktree. A worktree is
  never removed while uncommitted work would be lost.
- **`worktree-remove` / `worktree-guard` (#369/#389).** `python3 kaola-dispatch.py
  worktree-remove --repo R --path P [--force] [--assume-clear] [--live ROWS] [--skills-root S]`
  relocates its own cwd out of P first (`actions: [{action: relocated, occupant: self}]`); a
  failed relocation is itself a warning and does not stop the removal. It then runs
  `git -C R worktree remove [--force] -- P` unless a live process cwd and uncommitted
  changes hold at once (the one cwd hard block: `result: deferred`, `reason: cwd-occupied`,
  exit 3 and a `route`). A live cwd or an unreadable probe alone proceeds with a typed warning. A
  post-check repeats the occupancy probe: a live cwd that appeared between check and remove, or
  a process whose cwd was just deleted, is repaired by recreating P as an empty directory
  (`result: removed`, `action: placeholder-restored`, `post_check`, warning). An unverifiable
  post-check adds no placeholder and never undoes the removal. `--assume-clear` is accepted for
  compatibility and no longer changes the outcome. `worktree-guard` is the read-only form.
  `--all-user-processes` widens the probe to this uid.
- **The `worktree-guard` receipt is a frozen consumer contract (#374/#389).** Kaola-Workflow
  locates the Runner through `kaola-project-runner-locate receipt` (`root.path`) and runs
  `python3 <root>/scripts/kaola-dispatch.py worktree-guard --repo <project root> --path
  <worktree>` before each of its own `git worktree remove` calls. The fields below are that
  consumer's contract; `tests/contract/test-issue-374-worktree-guard-contract.py` is in the
  `./scripts/validate.sh` inventory and asserts the exact key sets, so renaming or dropping one
  breaks KPR's own gate before a consumer does.
  - Top level: `schema` (`kaola-worktree-remove/1`), `repo`, `path`, `result` (`clear` |
    `occupied` | `unverifiable` | `refused`), `occupants`, `probe`, `warnings`, and `route` on
    every non-clear answer (including `refused`). `warnings` is always present, `[]` when there is
    no recoverable finding.
  - `result` is the classification, not the block signal. `occupied` means an occupant exists;
    `unverifiable` means the probe could not answer. The exit code decides: `0` proceeds, even
    for a warning-only `occupied` or `unverifiable` answer; `3` is the hard block, returned only
    when a live process cwd is inside the worktree AND the worktree has uncommitted changes;
    `2` is `refused` (for example `repo-missing`).
  - `warnings[]`: `code` (`occupied-cwd-recoverable` | `cwd-unverifiable`), `path` (the
    worktree), `detail` (the recoverable finding), and `recovery` (the executable repair/recheck:
    `cd <repo>` for the occupant shell plus a `worktree-guard` recheck, or the wider
    `--all-user-processes` recheck). A recorded-only cwd is `occupied-cwd-recoverable` as well.
  - `occupants[]`: `pid`, `ppid`, `exe_basename`, `cwd`, `cwd_deleted`, `source` (`process` |
    `recorded`), and `session` (`null`, or `{platform, session, role, holder_instance_id}`).
  - Exit codes are stable for script consumers: `0` = proceed; `3` = the one hard block
    (`occupied` + live cwd + uncommitted changes; the receipt is still valid JSON); `2` =
    `refused`.
  - Coverage: `_sweep_list` reads one `list --include-dead` and `trees_from_rows` keeps every
    `identity: verified` row whose `repo` is the repo or the target, without filtering
    `session_role`. A Host, a Sideagent and a seat (worker) therefore each contribute their
    process tree and recorded `tool_cwd_path` to the occupancy answer.
- **W2** a `prunable` worktree entry inside ROOT: `git -C ROOT worktree prune`, once per apply.
- **B1** (#357) a local `workflow/issue-N` branch whose issue is CLOSED, not checked out in
  any surviving worktree (a branch still held by a kept or skipped worktree lands in
  `skipped` as `checked-out` - the worktree item owns that decision, so a branch is planned
  only when every worktree holding it is itself a W1/W2 candidate this scan), with no live
  verified session for issue N, and merged: its tip an ancestor of the remote head
  (`merge: "ancestor"`, deleted with `git branch -d`) or equal to the merged PR's `headRefOid`
  (`merge: "merged-pr-head"`, deleted with `git branch -D` on exact SHA equality only -
  on GitHub a merged PR head stays fetchable at `refs/pull/<PR>/head` after the remote
  branch is gone; verified 2026-10-19 on this repo: PR #134 `workflow/issue-133`,
  `refs/pull/134/head` = `394caf77`). Otherwise kept `unmerged-or-unpushed`. Remote branches
  are never deleted (no push). Restore with `git branch workflow/issue-N <sha>` (the
  candidate's `restore` field). Apply re-verifies the tip SHA, the worktree list, one extra
  `list --include-dead` (one per branch phase, only when a branch item is planned) and the
  merge state.
- **F1** a regular `*.tmp` file directly in `.kaola/` older than 24 h
  (`SWEEP_STALE_SECONDS`). Nothing else in `.kaola/` - state, backups, dispatch indices,
  locks, webhook files, session records - is touched.

Three report-only rules (#357) list residues in the receipt's `report` for the Owner or
Host - never in `candidates`, `kept`, `alerts`, `last_sweep` or `maintenance`, and the
sweep never removes them:

- **R1** a direct child of `kaola-workflow/` that is a real directory (not `archive`, not
  dot-prefixed) holding `workflow-state.md` whose `issue_number:` names a CLOSED issue:
  `{id: workflow-folder:<resolved>, rule: R1, kind, issue, path, status, next}` points at
  the Kaola-Workflow finalize the Host still owes.
- **R2** a top-level `.kaola/` child that is no Project Runner artifact
  (`SWEEP_KAOLA_OWN`), no `*.tmp`, no R3 backup and not `target` or `build` (those two are
  never scanned and never reported): `{id: kaola-foreign:<path>, rule: R2, kind, path,
  type: file|dir|symlink|other, bytes, incomplete?, next}`.
- **R3** regular heartbeat-prompt backup copies in `.kaola/` (`heartbeat-prompt.v*-*.json`):
  one `{id: heartbeat-backups, rule: R3, kind, count, bytes, next}` item.

Completion is a forge fact only: the issue is CLOSED. Issue #353 batches the lookup: one
`gh api graphql` call per chunk of 50 issues (issue state plus merged PR heads for
`workflow/issue-N` in one query, `KAOLA_SWEEP_FORGE_TIMEOUT` seconds, default 20). An
answered but unusable call (nonzero exit, unparseable JSON, a missing issue or non-string
state) falls back to the serial per-issue `gh issue view` + `gh pr list` path for ALL
issues; a timeout or OSError answers `forge: "unavailable"` directly with no fallback - a
stuck `gh` would hang the fallback too. `gh` failing is `forge: "unavailable"`: every
issue-linked item goes to `skipped` as `forge-unknown`, never to kept, and nothing is
removed. An open issue is silently not a candidate. Only issue numbers appearing in
sessions, worktrees, local `workflow/issue-N` branches or active Kaola-Workflow folders
are queried. Merged-PR heads are a set per issue - any merged head
matches.
`--dry-run` writes nothing at all (no state write, no prune, no stop, no fetch); it still runs
the read-only list/status/gh/git calls.

`--apply` needs an identity: the verified Host carrier of this repo (plan = the current scan),
or the bound node with `--batch B`, verified like `recovery-input` batches - the node record's
dispatcher is this repo's Host carrier and that carrier's events hold `sideagent_node_batch`
with `batch` B, `target_holder` the caller, and a `sweep` object; the plan is then that event's
`sweep.candidates`. Since #353 apply re-verifies only planned candidates, never a rescan: a
Host apply reuses its own scan's forge facts; a node apply rebuilds items from the stable
plan ids, spends one batched forge call and one `git worktree list`, and gates sessions,
worktrees and branches on issue CLOSED (`forge: "unavailable"` → `forge-unknown`; a
reopened issue is `no-longer-candidate`). Per candidate the
checks are re-verified right before removal; each worktree removal spends one global
`list --include-dead` and an unanswered list is `skipped` as `acp-unknown`, never removed.
The event's `sweep.kept` (the dry-run receipt's kept list) seeds `sweep-kept`; planned items
that re-verify kept join it. Only planned ids still candidates are applied (others land in
`skipped` as `no-longer-candidate`; new candidates wait for the next sweep). Apply order:
sessions, worktrees, prune, branches, files (the branch phase spends one extra
`list --include-dead`, only when a branch item is planned). Then, under the state lock, `maintenance.last_sweep` is
written and the kept alert synced. Since #353, `--apply` and `--record-empty` validate the
state file BEFORE any scan or action (`require_current`); a refusal exits 2 carrying the
existing reason (`state-missing`, `legacy-format`, `schema-unsupported`,
`state-unreadable`) plus a `recovery` hint with the exact `state` command(s); nothing is
stopped, removed, pruned or written. `--dry-run` keeps its tolerant read. Any other caller
is refused (nonzero exit). `--record-empty` is Host-only: a re-scan
with candidates answers `result: candidates` and writes nothing; otherwise it writes
`last_sweep` (`batch` null) and syncs the alert - `recorded-empty`.

`maintenance.last_sweep` is `{at, key, batch, holder, accepted_revision, head, removed}` -
one current fact overwritten per sweep, like `last_checkpoint.settled`, never a history.
`accepted_revision` is the Host carrier's record (`accepted_revision` of the caller's own
record for a Host apply, of the dispatcher record for a node); `head` is `rev-parse HEAD` or
null; `removed` lists this sweep's removed ids. It never appears in the Host view `attention`
and does not change its fingerprint. Items kept are reported in `alerts["sweep-kept"]`
(owner `host`, level `warn`): `inputs` maps each kept id to `{why, evidence, next}`, written
by `tool:sweep` with the caller's `writer_holder`, rewritten only when the kept set changes
(an identical kept set leaves the alert's bytes untouched) and removed atomically when the set
empties. No other routine field holds kept or removed text. `last_sweep` itself is written on
every apply and record-empty: it is the due mark and a node batch's checkpoint, so `at`,
`batch`, `head` and `accepted_revision` move even when nothing was removed. A second run is a
no-op in actions only - no stop, no remove, no prune, no file deletion, alert unchanged.

The Host carrier runs the sweep due check inside the existing node relay boundary - only in
node mode, only for a `session_role: host` holder, no new thread, loop or timer. Due when
`last_sweep` is absent (`first`), the carrier's accepted revision differs (`upgrade`), HEAD
moved (`merge`), or `at` is older than the interval (`interval`; `KAOLA_SWEEP_INTERVAL_HOURS`,
positive float hours, default 24, invalid falls back to 24). An event only makes it due
earlier; once a sweep records the new head/revision it is handled. Not due spends nothing but
the cheap `rev-parse` - no scan subprocess, no event, no node, no wake. Due runs
`sweep --dry-run` in a daemon thread. Since #353 the tool child is bounded by
`SWEEP_SCAN_TIMEOUT_SECONDS` (600 s): it runs in its own process group and a timeout kills
the group. A scan error - or since #353 any receipt with a non-empty `timed_out` - is one
`sideagent_sweep_scan_failed` event, cools down for the interval, and never runs
record-empty or queues a batch; a plain `forge`/`acp` `"unavailable"` without a timeout
keeps the existing planned/record-empty behaviour. Anti-starvation (#353): a due sweep that
keeps losing to pending reconcile input becomes overdue (immediately when the `interval`
reason is twice the interval old, otherwise once deferred for one interval) and then runs at
the idle boundary even with input pending; still never during a Host turn. No candidates runs `sweep --record-empty`, moves the due mark
and appends `sideagent_sweep_empty` - no node, no staged Host event, no wake, `host_revision`
unchanged. Candidates queue exactly one batch keyed by `key`. The send reuses the reconcile
start/send path (a fresh node from the recipe when no live node target): batch id
`s-<sha256([target holder, key])[:12]>`, one prompt carrying the exact
`sweep --apply --batch B` command, and a `sideagent_node_batch` event with `batch`,
`target_holder`, `host_holder`, the unchanged handled `host_revision_through`,
`prompt_fingerprint` and `sweep: {key, candidates, reason, kept}` (kept = the dry-run
receipt's kept list, replayed by the node apply). A sweep batch never touches
`sent_through`, `recovery_sent`, `sent_prior` or the handled/acked revisions, never writes a
`maintenance-returned` row and never calls the maintenance-failure path; a lost or unadmitted
sweep node is staged to the Host with `record=False` or kept queued when the runtime moved.
Settle is verified only when `last_sweep.batch` is the batch, `last_sweep.holder` the node
holder and the turn completed; `sideagent_sweep_settled` carries `batch`, `holder`, `key`,
`checkpoint` (`verified`|`missing`), the durable `removed` receipt and `host_woken`. Verified
with a node-written attention change wakes the Host once (`maintenance sweep batch B verified;
Host attention changed`); verified otherwise is quiet (`node_quiet`); unverified reaches the
Host once (`checkpoint missing`) and is not re-queued inside the interval; a runtime-refused
turn moves the runtime like a reconcile batch and keeps the sweep queued. The node is then
exact-stopped as today. Without an active node binding there is no periodic sweep - the Host
can run the tool itself; at final close-out the Host runs one `sweep --apply` itself before
cancelling the heartbeat
(`templates/orchestrator/references/doc-maintenance.md`); `--dry-run` needs no caller
identity and writes nothing, so a Delegator may run it read-only to report residue.
Holders advertise `sideagent-sweep/1`.

## Delegator webhook wake (#299)

A Host holder (and only a `session_role: host` holder) fires a wake signal when
the Delegator must act, so a webhook-armed Delegator does not wait for its next
cron heartbeat. The line is "does the Delegator need to act", not "fewer wakes".
There is no time throttle, minimum interval, or coalescing. The holder spawns a
detached child — `python3 kaola-acp.py delegator-webhook deliver` with the payload
on stdin — that never blocks the holder, survives holder exit, and does the
network and retry work itself. The child argv carries no secret and never contains
the string `kaola-acp-holder` (process scans match that name).

The holder decides from facts it can see: the ended turn's prompt source, whether
the next beat is already admitted or a Delegator after-turn steer is queued,
undelivered Host attention in `.kaola/heartbeat-prompt.json`, pending
`state.decisions` rows in that same file, staged worker events, and the turn's
stop or exit state. Prompt source is `delegator` for a socket prompt or a steer,
and `self` for a worker-event delivery, a compact reload, or a compact notice.
A socket client cannot set that source. A Delegator decision has to be a
`state.decisions` row (`owner` `delegator` or `user`). A note only in
`.kaola/run/*.md`, or only in the turn text, is not that row and does not wake.

Always wake (a real stop must not end silently):

| what the holder saw | state | state_detail | reason |
| --- | --- | --- | --- |
| new `session/request_permission` | `blocked` | `permission_required` | `permission_required` |
| `turn_failed` | `error` | `turn_failed` | `turn_failed` |
| unrequested agent exit outside the boot window | `error` | `agent_exit` | `agent_exited` |
| failed boot | `error` | `boot_failure` | `boot_failure` |
| `op_stop` after the stopped record is written | `stopped` | `exact_stop` | `exact_stop` |
| dead holder recovered by the next `start`, a dead-holder `stop`, or cron `delegator-webhook status` | `error` | `holder_lost` | `holder_lost` |

`turn_failed`, permission, agent exit, boot failure and exact stop wake even when
the prompt source was the Delegator. Exact stop is spawned inline because the
holder exits with its reply. A canceled turn under a requested stop does not
send its own wake; exact stop covers it.

Host-initiated wake (Issue #317, Yanlei 2026-10-14 00:46). The Host calls
`kaola-acp.py <platform> wake --repo REPO --session SESSION --reason REASON`
on its own holder. `REASON` is `needs_decision` (a decision, a grant, or a
blocker), `question_waiting`, or `delivery_review`. The holder appends
`delegator_wake_requested` and sends at that call. Seats may still be in a
turn. The all-idle latch, a Delegator-caused turn, and a live `send --wait`
do not suppress it, and the call does not set or clear the latch. `state` is
`end_turn`. `state_detail` is `host_initiated`. Each call is a new
`event_seq`. A second deliver of that pair does not POST. Any other reason
is refused and sends nothing. A session that is not the Host is refused.
No new reason word.

The two rules are the core model. Rule 1 is the all-ended `all-idle` below.
Rule 2 is this call. Folded into them: a silent turn and the stop re-check
are rule 1, not a second idle wake; a decision, question, or delivery review
the Host wants sent while seats still work is rule 2, not a new per-turn
reason. Kept, because they are different facts: `permission_required`,
`turn_failed`, `agent_exited`, `boot_failure`, `exact_stop`, and
`holder_lost`. Also kept: the turn-end attention scan when no seat is in a
turn (Issue #315), and `host_stopped_pending` or a refusal `needs_decision`
while a seat is still in a turn. A stuck seat is rule 2 when the Host judges
it stuck; this issue adds no timer. A Host crash or hang stays the #299
`holder_lost` backfill. A delivery failure is #318 and is not a wake here.

A completed turn, or a cancel that was not requested, wakes only when the
Delegator is not already there and the Host did not continue by itself:

| what the holder saw | reason |
| --- | --- |
| next beat already admitted, or a Delegator after-turn steer is queued | no wake |
| no active seat turn, and an undelivered attention row or an open `state.decisions` row is pending | the attention reason below; not `all-idle` |
| no active seat turn, that list is empty, and this all-ended episode has not yet sent `all-idle` | `all-idle` |
| no active seat turn, that list is empty, real work has resumed since the last `all-idle`, and the Host is all-ended | `all-idle` once, even if the turn is the Delegator's and the previous latch was set |
| no active seat turn, that list is empty, this all-ended episode already sent `all-idle`, real work has not resumed, and a Delegator turn admitted without `--wait` ends | `host_turn_done` once for that turn |
| the same, but the turn is a self turn or was admitted with `--wait` (a `--wait` caller usually already has the result; a timeout or a caller that disappears is not decided here) | no wake |
| prompt source `delegator` (this send or steer) and a seat still has an active turn | no wake |
| undelivered host-view row `kind=decisions`, `why=host-decision` | `question_waiting` |
| undelivered host-view row `kind=tasks` and `why` one of `awaiting-verdict`, `delivery-open`, `verdict-missing` | `delivery_review` |
| undelivered `why` `registered-decision` row, or an `alerts` row with `why` `severe` | `needs_decision` |
| any other undelivered attention row (a `holds` row owned by the host, a non-severe Host alert such as `maintenance-returned`, a `maintenance` or `sideagent` duty, a `transcribed-check`) | no wake of its own (Issue #324) |
| a seat still has an active turn, and a staged worker event has no prompt fingerprint, an overflow is unconfirmed, or the stop is `max_tokens` / `max_turn_requests` / `length` | `host_stopped_pending` |
| a seat still has an active turn, and the stop is `refusal` or the cancel was not requested | `needs_decision` |
| clean `end_turn` with nothing pending, while a seat still has an active turn | no wake |

Undelivered attention means the heartbeat body is a host view (`view` `host`,
`attention` a list) whose fingerprint is not the one last delivered on a
worker-event prompt. A standing Host-owned row whose `content` digest moved
(the Host or its Sideagent node edited a hold or the `maintenance-returned`
alert) counts as undelivered, but it is Host bookkeeping, not a question for
the Delegator: a compaction-reload turn that ends beside a Sideagent node
settle, with `state.decisions` empty, sends nothing (Issue #324). Checked in
that order. Self-continuation wins over
everything below it (no wake): the Host has not gone idle. A working seat is
a running holder whose record names this Host instance as `dispatcher`, whose
`session_role` is not `sideagent` or legacy `sidekick`, whose `state` is
not `agent_exited`, `stopping`, or `stopped`, and whose record shows an
active turn (Issue #314). `record.json` does not store `turn_active`. The
scan reads `last_prompt.mutation_status` from that file, with no socket read.
The holder writes `in_progress` in the same locked admission that starts the
turn, and `completed` when the turn ends. An in-memory move to `accepted`
does not rewrite `last_prompt`, so `in_progress` stays the active-turn mark
for the whole turn. `accepted` stored in `last_prompt` counts as active too.
`completed`, `not_started`, a missing `last_prompt`, and a prompt object with
no `mutation_status` are not an active turn: a ready seat held for acceptance
does not block `all-idle`. Any other `last_prompt` shape is unknown — not a
JSON object, or a `mutation_status` outside that set, including `unknown` and
JSON null — and still blocks. A false `all-idle` would say nobody is working
while that seat's turn cannot be read. Stop preservation uses the scan
without this turn filter, so an idle held seat is still kept. The bound
Sideagent node is not a seat. An open `state.decisions` row has `owner`
`delegator` or `user` and `status` other than `settled` (a missing status is
open). `owner` `host` is already attention (`why` `host-decision`) and is not
added again. When no seat has an active turn, the holder merges each open
delegator or user row as `why` `registered-decision` and classifies that list
before the `all-idle` fallback (Issue #315). The episode latch does not
suppress that reason. A compaction reload does not skip it:
`compact_reload_delivered` admits an ordinary self prompt, and a verified
maintenance checkpoint does not bypass the turn-end check. The reload does
not clear the latch. Each later Host turn that ends with no active seat wakes
again while the row stays pending. There is no once-per-decision latch.
When that list is empty, the turn would otherwise be silent, including a
length stop or a refusal, and the wake is `all-idle`, once per all-ended
episode. Owner rule, Yanlei 2026-10-11 16:49, narrowed 2026-10-13 for a
registered decision, and extended 2026-10-14 (Issue #317): when the Host
turn is not active, no follow-up is queued, and no seat has an active turn,
that is one all-ended episode. The wake is `all-idle` once. A
Delegator-admitted turn does not suppress it, and a latch carried from an
earlier episode does not either. The same episode does not wake again.
`event_seq` dedupe still applies; the new episode's wake is a new event.
The episode latch starts clear, so the first time the holder observes that
state it wakes once. A Delegator-admitted turn (socket `send` or steer) does
not by itself open the next episode. If this episode already sent `all-idle`
and real work has not resumed, the turn returns no wake. Real work is a
working non-exempt seat (a re-check or the turn-end scan), a non-exempt
worker stopping, or a self turn that delivers worker events. That work arms
the next episode. At the following all-ended transition the previous latch
is cleared once, then one `all-idle` is sent, including when the turn is the
Delegator's and including when that turn stops the last working seat. A live
`send --wait` or `op_wait` caller who has not returned, timed out, or lost
the reply write is not all-ended yet; the same one wake runs after that
caller is gone. A later Delegator turn that ends still idle, with no real
work in between, does not wake again when it was admitted with `--wait`; an
unconsumed `--no-wait` Delegator turn still sends one `host_turn_done`
(Issue #392), and the episode latch is unchanged. A self turn with no working
seat still names `all-idle`; the episode latch sends it only when due, so a
self-continuation that ends with no change after `all-idle` was already sent
does not POST again. A self turn that delivers new worker events clears the
latch, and the next all-idle transition wakes once. A `ps` failure looks like no seats and,
when the latch is clear, wakes `all-idle`. With a seat still working, a
Delegator-caused turn does not wake, and a waiting question wins over a
delivery review. An explicit `wake` call still sends while that seat works. `state` for these rows is `end_turn`. `state_detail` stays
the agent's ACP `stopReason` when it is a clean token, otherwise `"other"`,
`"cancelled"`, or null, as in the table below.

The same condition is checked again when a stop lands after the Host's last
turn has already ended. Two points re-check it. A confirmed
`sideagent_node_stopped` (the node process is gone; an unconfirmed stop does
not) re-checks after the holder kicks worker events. A dispatched worker
`terminated` event re-checks after that event is staged, which is also when
`stop` of the last worker reaches the Host. The wake is sent only when every
one of these is true: this holder is the Host; stop was not requested and the
holder is not `stopping` or `stopped` (exact stop owns that wake); the Host
turn is not active and no Delegator follow-up is queued; the last turn
outcome is `turn_completed` or `turn_canceled`; and no working dispatched
seat remains. The check is non-blocking, the same detached deliver child as
every other wake, and there is no time throttle. One all-ended episode sends one
`all-idle`. The latch clears when a re-check or a turn-end scan still sees a
working non-exempt seat, when a non-exempt worker terminates, or when a self
turn delivers new worker events. A Delegator-admitted turn does not clear it
unless that scan sees a working seat. If the latch was still set when real
work had already resumed, the all-ended transition clears it once before the
wake (Issue #317). A later non-exempt worker termination can wake again. The stop-time payload is `state`
`end_turn`, `state_detail` `end_turn`, `reason` `all-idle`. The Host is
already idle, and this stop is not a new turn and not an exact Host stop, so
`stopped` / `exact_stop` stay reserved for `op_stop`. That stop re-check
sends only `all-idle`. It does not read `state.decisions`. A registered
decision is classified at the next Host turn end, and the latch does not
suppress that reason. A turn-end `all-idle`
whose agent stop reason was `end_turn` has the same shape. Dedupe is still
`holder_instance_id` + `event_seq`. A second deliver of that pair does not
POST, and a later stop in the same idle episode does not POST again.

A Host holder that dies without signalling (SIGKILL, crash) is covered by the
CLI, not the holder: `start` replacing a dead or pid-reused record and a
dead-holder `stop` (`force_kill_from_record`, the pid-reused branch of
`force_stop_unreachable`) emit exactly one `error`/`holder_lost` wake on the
dead instance's behalf before the record is rewritten or retired. Exactly-once
across process death is a `delegator_death_wake` event appended under an flock
on `delegator-death-wake.lock` in the record dir; the event's cursor is the
wake's `event_seq` (the EventLog cursor continues across holders in one record
dir), so the recovered wake is a new event and not a duplicate of an earlier
wake from that holder. The start/stop receipt names the outcome under
`delegator_death_wake` (`sent`, `holder_instance_id`, `event_seq`, or a
`reason` of `already-recovered`/`spawn-failed`/`death-wake-unrecorded`).
`stamp` treats `sent: false` as a failure and attaches the route on that
nested object. `spawn-failed` says the wake was not attempted: run
`delegator-webhook test`; if that delivers, continue the inquiry now.
`wake-spawn-failed` is the same sentence. That is not a Host session
restart. `acp-spawn-failed` still is. `already-recovered` keeps its
self-route. A lock or event-log `OSError` used to omit the key. It now
returns `sent: false` and `reason` `death-wake-unrecorded`: the death wake
was not recorded; read the holder event log, then run `delegator-webhook
status` and `test`. If test delivers, continue the inquiry. Do not treat
the omitted wake as delivered. The exception text is not stored.
CLI, not the holder. `start` on a dead or pid-reused record, and a dead-holder
`stop` (`force_kill_from_record`, the pid-reused branch of
`force_stop_unreachable`), emit exactly one `error`/`holder_lost` wake on the
dead instance's behalf. Wake eligibility is the dead holder (Issue #319). A
live `agent_pid` or `agent_pgid` does not suppress that wake. `stop` emits it
and then sweeps the recorded agent. `start` emits it and replaces the record
only when both recorded agent pids are dead. While either recorded agent pid
is alive, `start` leaves the record in place and returns `outcome`
`holder_lost`. That receipt's `record` carries `agent_pid` and `agent_pgid`,
and `error.agent_pgid` repeats the group id. The wake payload does not carry
those pids. The receipt's `route` is the `holder-lost` route: exact-stop the
orphaned agent (`stop --repo REPO --session SESSION
--expected-holder-instance-id ID`), attest, then `start --resume NATIVE_ID`.
If resume fails, start a fresh Host and hand it the summary from `status`,
`capture --lines 200`, `list --repo --include-dead`, and delegator view.
Exactly-once across process death is a `delegator_death_wake` event appended
under an flock on `delegator-death-wake.lock` in the record dir; the event's
cursor is the wake's `event_seq` (the EventLog cursor continues across holders
in one record dir), so the recovered wake is a new event and not a duplicate
of an earlier wake from that holder. The start/stop receipt names the outcome
under `delegator_death_wake` (`sent`, `holder_instance_id`, `event_seq`, or a
`reason` of `already-recovered`/`spawn-failed`).

`delegator-webhook status` is a third caller (#311). It does not replace or
retire the record, and it does not need a new Host start. The Delegator's
low-frequency cron fallback is an Agent inquiry, not a daemon. Its native
timer body is unchanged. The loaded Skill cadence sentence is what runs
`delegator-webhook status --project` on that inquiry. Only the `status`
action scans. `test` sends one `state: test` wake and does not scan.
`configure` prints the status receipt and does not scan.

The scan runs only when the project entry exists, validates, and `enabled`
is true. It walks record files for that project and calls
`recover_host_death_wake` when all of these hold: `session_role` is `host`,
`state` is not `stopped`, `holder_instance_id` is a non-empty string, the
record repo is this project, and `holder_pid` is dead (`pid_alive` is false
for a missing pid). A live `agent_pid` or `agent_pgid` stays eligible
(Issue #319). The wake payload stays `state` `error`, `state_detail`
`holder_lost`, `reason` `holder_lost`, and does not include those pids.
The same `delegator_death_wake` flock and event apply, so a second `status`
returns `already-recovered` and does not POST again. `status` returns as soon
as the deliver child is spawned. It does not wait for the network.

A missing config, `enabled: false`, `config-mode`, or `invalid-config` sets
`holder_lost.scan` to `skipped` with `reason` `not-enabled` or that config
error, and `wakes` empty. A skipped scan writes no death event, so a later
enabled `status` can still send the wake. A live `holder_pid` is not woken
here, including a pid whose argv is no longer the holder: `status` does not
probe argv. That reused-pid case stays with the next `start` or dead-holder
`stop`. Record replacement is separate, and only `command_start` does it.
A live `agent_pid` or `agent_pgid` blocks that replacement. The start receipt
then carries the live agent pids (`record.agent_pid`, `record.agent_pgid`,
`error.agent_pgid`) and the `holder-lost` route. The record stays until an
exact stop of the orphaned agent.

The CLI does not poll and does not read `cadence.interval_minutes`. Nothing
else in the runner polls webhook state. The cadence bound is the Delegator's
recorded cron interval. The Skill's example interval is 120 minutes. After
the Delegator has loaded the cadence line, the wait from a holder death to
this wake is at most one cron interval, plus delivery. A record-root mismatch
(`RecordRootMismatch`) returns `holder_lost.scan` `incomplete`, `reason`
`record-root-mismatch`, and an empty `wakes` list. `stamp` attaches the
existing self-route: pass one private `--record-root` you own, or unset
`KAOLA_ACP_RECORD_ROOT`. Do not write session files on the refused root.
`leg` is always `delegator-webhook status`. The scan does not wait for the
network.

The same scan also cross-checks the host registry (#359). A `start` whose
`session_role` is `host` writes one row per session to
`<repo>/.kaola/host-registry.json` (`kaola-host-registry/1`, mode 0600, atomic
replace under `host-registry.lock`): platform, session, realpath repo, record
dir, socket path, holder pid, `holder_instance_id`, `acp_session_id`, and
agent pids. A recorded clean stop removes the row. A row whose
`(platform, session)` has no `record.json` under any record root is a wiped
record directory: `status` emits the one `error`/`holder_lost` wake with
`state_detail` `record_lost` at the fixed `event_seq` 0, and marks the row
(`record_lost_wake`) so a later `status` reports `already-recovered` instead
of POSTing again; the claims file backs the same (id, seq) dedupe. A row
whose record exists and is `stopped` is pruned; a newer `holder_instance_id`
refreshes the row's facts. The findings land on `holder_lost.record_lost`
(`{scan, lost}`); each lost entry carries the session, `holder_instance_id`,
`holder_pid_alive`, and a `recovery` block naming the executable path —
`stop --repo REPO --session SESSION --force` sweeps a live argv-verified
orphan holder (a reused pid is never signalled), then `start --resume` on the
recorded `acp_session_id` starts a clean one. `status`, `observe`, `send`,
and the other session ops on that session return `error.code` `record-lost`
with the same `record_lost` facts; `list --repo` reports them under
`records_lost`; a plain `stop` on a live orphan refuses `record-lost`; and a
`start` while the orphan lives refuses `record-lost-orphan`. A
`record_lost.scan` of `registry-unavailable` means the registry could not be
read or locked; lost rows are not reported on that pass.

Payload (signal only, no transcript, prompt, diff or secret). A current
holder (v0.9.7 and later) sends `reason`, one of the tokens in the tables
above, or `test`. A previous holder's payload may omit it; the accepted-shape
rule below says which omissions `deliver` still POSTs:

```json
{"schema": "kaola-delegator-wake/1", "project": "<repo realpath>", "session": "<--session>",
 "holder_instance_id": "<holder instance>", "event_seq": <events cursor>, "state": "end_turn",
 "state_detail": "max_tokens", "reason": "host_stopped_pending", "ts": "YYYY-MM-DDTHH:MM:SSZ"}
```

On every shape except the pre-`state_detail` key set, `state_detail` is
present (a string matching `^[A-Za-z0-9_.:-]{1,64}$`, or null). It is not the
wake reason:

| state | state_detail |
| --- | --- |
| `end_turn` | the agent's ACP `stopReason` verbatim (`end_turn`, `max_tokens`, `max_turn_requests`, `refusal`, `cancelled`, …) when it is a clean token, else `"other"`; `"cancelled"`/`null` when the agent reported none |
| `blocked` | `permission_required` |
| `stopped` | `exact_stop` |
| `error` | `turn_failed`, `agent_exit`, `boot_failure`, or `holder_lost` (death recovery above) |
| `test` | `test` |

Only `session/request_permission` produces `blocked`. An owner question asked
only in reply text is an ordinary `end_turn` and does not by itself wake; a
`question_waiting` wake requires an undelivered host-view `decisions` /
`host-decision` row. The stop reason is whatever the agent reports: codex-acp
maps a failed turn to `end_turn`, which #173's systemError detection turns into
`error`/`turn_failed`.

Delivery: POST the payload as the JSON body with `Content-Type: application/json`
and `User-Agent: kaola-delegator-wake/1`, plus the configured key header for a
`header` attachment. Redirects are refused (`redirect-refused`, no retry). Each
attempt times out at 12 s. One initial attempt plus up to 3 retries (4 attempts,
backoff 1 s, 2 s, 4 s). The retryable set is connection errors, HTTP 400,
HTTP 408, HTTP 429, and HTTP 5xx (#311; this supersedes the #302 rule that
HTTP 400 was final). A client timeout is not retried: the server may already
have accepted the POST. HTTP 401, 403, and 404 are final on attempt 1, and so
is every other non-2xx that is not in the retry set (including 405, 409, and
422) and `redirect-refused`. A 2xx is `delivered`. Not
configured or `enabled: false` writes one `skipped` receipt with
`skip_reason` `not-configured` and no network, and does not consume the event;
invalid config or mode writes one `failed`/`invalid-config`/`config-mode`
receipt with no network and does not consume it either. Before the first
network attempt the sender claims `holder_instance_id` + `event_seq` under
the receipts flock (`.kaola/delegator-webhook-claims.json`, mode 0600, last
256 pairs). A second deliver of that pair writes one `skipped` receipt with
`skip_reason` `duplicate` and does not POST. The claim stays after success
and after final network failure. A death-recovery wake uses a new
`event_seq`, so it is not that duplicate.

Accepted payload shapes (#304). `deliver` is a new process per wake. A holder
that is still running an older build sends the shape it was started with, and
that wake must still be POSTed. The POST body is the payload as received: a
missing `reason` is not filled in. Three exact key sets are accepted (no
extra keys). Every set has `schema` `kaola-delegator-wake/1`, `state` in
`{end_turn, blocked, error, stopped, test}`, and an integer `event_seq`
(a boolean is not an integer).

| shape | keys | `reason` | `state_detail` |
| --- | --- | --- | --- |
| v0.9.7 and later | core + `state_detail` + `reason` | required, closed vocabulary | required: null or a token |
| v0.9.5 / v0.9.6 | core + `state_detail` | optional, default absent | required: null or a token |
| first #299 sender, before `state_detail` (`843902e2`) | core only | optional, default absent | optional only on this key set |

Core keys, required in every accepted shape: `schema`, `project`, `session`,
`holder_instance_id`, `event_seq`, `state`, `ts`. `reason` is optional and
defaults to absent: the receipt records JSON null, and the sender does not
invent a wake token. `state_detail` is optional only for the key set that
predates it. A payload that has `reason` must be the current nine-key shape
(`state_detail` present and valid). A present `reason` outside the vocabulary,
a wrong schema, an extra key, or a missing core key is refused — exit 1, and
one `failed`/`invalid-payload` receipt when the project resolves. An invalid
payload does not claim the event.

Per-attempt receipt (`error` is a classified code, never an exception message
— urllib errors can embed the URL). `delivered` and `failed` include `reason`
and no `skip_reason`. `reason` is the payload's string wake reason, or JSON
null when that payload had no string `reason` (an accepted previous shape, or
a refused payload that carried no string). A refused payload's `reason` is
copied when it is a string, including a string outside the vocabulary.
`skipped` includes `skip_reason` (`not-configured` or `duplicate`) and no
`reason` key.

```json
{"ts": "...", "state": "end_turn", "state_detail": "end_turn", "session": "...",
 "holder_instance_id": "...", "event_seq": 7, "reason": "delivery_review",
 "result": "delivered", "attempt": 1, "max_attempts": 4,
 "http_status": 200, "error": null, "response_body": null,
 "response_body_truncated": false, "response_headers": null,
 "elapsed_ms": 12, "final": true}
```

```json
{"ts": "...", "state": "end_turn", "state_detail": null, "session": "...",
 "holder_instance_id": "...", "event_seq": 8, "skip_reason": "duplicate",
 "result": "skipped", "attempt": 0, "max_attempts": 4,
 "http_status": null, "error": null, "response_body": null,
 "response_body_truncated": false, "response_headers": null,
 "elapsed_ms": 1, "final": true}
```

```json
{"ts": "...", "state": "error", "state_detail": "turn_failed", "session": "...",
 "holder_instance_id": "...", "event_seq": 9, "reason": "turn_failed",
 "result": "failed", "attempt": 1, "max_attempts": 4,
 "http_status": 400, "error": "http-status",
 "response_body": "{\"error\":\"rejected\"}", "response_body_truncated": false,
 "response_headers": {"content-type": "application/json", "retry-after": "3",
  "x-request-id": "req-1"},
 "elapsed_ms": 20, "final": false}
```

Every attempt row includes `response_body` (string or null),
`response_body_truncated` (boolean), and `response_headers` (object or null),
including skipped and invalid-config rows. Only an HTTP error response
(`error` `http-status`) fills the body and the headers. The sender reads at
most 8192 bytes, replaces the configured URL and sender key — and each
value's percent-encoded form — with the token `[redacted]`, then stores at
most 512 characters. Redaction runs on that read window before the stored
cut, so a secret that fits in the window is removed whole. An empty body is
null. `response_body_truncated` is true when the read hit 8192 bytes or the
redacted text was longer than 512 characters. `response_headers` keeps only
`content-type`, `retry-after`, `www-authenticate`, `x-request-id`, and
`x-correlation-id`. Names are stored in that lowercase form. Each value is
redacted and cut at 200 characters. Any other response header is dropped.
No header has its own truncated flag. A 2xx, a timeout, a connection error,
a refused redirect, a skip, and an invalid config store a null body,
`response_body_truncated` false, and null headers. Exception text is not
stored. The URL and the sender key do not appear in the receipt file.

Receipts written before the skip-reason change put the skip cause in `reason`
(`not-configured` or `duplicate`) and omitted `reason` on `delivered` and
`failed`. Receipts written before #311 omit `response_body`,
`response_body_truncated`, and `response_headers`. `status` returns
`last_receipt` and `last_test` as stored, so every generation parses, and a
read does not rewrite the file. `last_test` is still
the newest stored receipt whose `state` is `test`. Readiness stays
`last_test.result == "delivered"`. A reader that classifies a skip uses
`skip_reason` when the key is present, and otherwise treats a `skipped`
receipt whose `reason` is `not-configured` or `duplicate` as that skip cause.

`error` is one of `timeout`, `connection`, `http-status`, `redirect-refused`,
`invalid-config`, `config-mode`, `invalid-payload`, `spawn-failed`, or null.
`spawn-failed` is the row the holder writes when the deliver child does not
start. Its `route` is the test-and-continue sentence, the same text as
`wake-spawn-failed`. The payload wake reason stays in `reason` and does not
replace that route.

A failed delivery row carries `route` only when `final` is true (#318).
HTTP 401 and 403: rotate the sender key
(`templates/kaola-delegator/references/webhook-wake.md` step 7), then `test`.
HTTP 404: reconfigure the URL, then `test`. A final HTTP 400, 408, 429, or
5xx, a final `connection`, a `timeout`, and any other final `http-status`
(for example 405, 409, or 422) say this wake was lost: run `status`, then
`observe`/`capture` for the recorded Host and the full standard inquiry; run
`test` once; if it delivers, nothing else is owed; otherwise stay
heartbeat-only and report. A non-final row (`final` false) has no `route`.
The sender is still retrying that deliver, and the row does not say to stop
for a final receipt. `redirect-refused`, `invalid-config`, `config-mode`,
and `invalid-payload` keep their own routes. The holder does not re-offer
the wake on a timer. The claim stays, so that `event_seq` is not POSTed again.

The Delegator inquiry treats `status.last_receipt` with `result` `failed`
and `final` true as a missed wake. The sentence is in
`templates/kaola-delegator/references/inquiry-report.md`: run the whole
inquiry, and never conclude that nothing is new from an empty webhook run.
`missed_event_seq` is not a payload field. The three accepted shapes above
are unchanged.

A run of final failed deliveries is one fact (#325). Per-event retry and the
per-receipt route stay as they are. Final rows whose `error` is
`http-status`, `connection`, or `timeout` join one run. A `delivered` row
ends that run. A skip, and a config or payload failure, neither joins it nor
ends it. `count` is distinct events: one HTTP 400 retried four times is one
event. The run is `repeated_failure` on the receipts file and on `status`
(`schema` `kaola-delegator-webhook-repeated-failure/1`):

| field | meaning |
| --- | --- |
| `window_start`, `window_end` | UTC stamps of the first and latest final failure in the open run |
| `count`, `min_count` | events so far, and 2 (more than one event) |
| `window_seconds` | 900. The window has passed when the span reaches this |
| `window_passed` | true once that span has been reached |
| `active` | true while `count` is at least 2 and the run has not ended |
| `host_notice` | one alert (`kind` `alert`, `once` true) for that `window_start`. Later events update `count` and `window_end` and do not emit again |
| `user_notice` | `once` while the run has opened the alert |
| `heartbeat` | `path` `heartbeat`, `bound_seconds` 7200, `applies` true only while the run is still failing and the window has passed |
| `fallbacks` | `retry`, `receipt-route`, `host-notice`, `heartbeat`, in that order |
| `ended_at` | set when a later delivery ends the run; null while it is open |

The sender writes one stderr line when the alert first opens. The holder
already copies that line into the event log. The sender does not add a wake
reason, does not start a timer, and does not send node traffic. When the
window passes, `heartbeat.applies` becomes true. 7200 seconds is the
heartbeat's own bound (the cadence example). The next heartbeat inquiry is
the remaining path.

When the routine webhook answers HTTP 400 for more than one event, tell the user once, with the window and the count.
The same `window_start` is not said again. The user is told at the end of
`fallbacks`, after the retry, the per-receipt route, and the one Host alert.

Final failed rows of that class are also stored in `failed_receipts`, apart
from the 32-attempt ring, last 256 (`failed_limit`). The next 32 delivered
attempts do not drop them. `status.failed_receipts_kept` is how many are
stored. `last_receipt` stays the newest attempt-ring row. A noticed run that
a new run replaces is `previous_repeated_failure`.

Receipts land in
`<repo>/.kaola/delegator-webhook-receipts.json`
(`{"schema": "kaola-delegator-webhook-receipts/1", "limit": 32, "failed_limit": 256, "receipts": [...], "failed_receipts": [...]}`,
last 32 attempts oldest-first, mode 0600, atomic replace under a sidecar flock).
A receipt-write failure prints one line on the deliver child's stderr and
does not crash the child. The line is the self-route: the POST may have
succeeded and this receipt was not stored; run `delegator-webhook status`
and `test`; if test delivers, continue the inquiry now; do not treat a
stale `last_receipt` as this wake. The line has no exception text and no
secret. The holder copies that stderr into its event log as
`delegator_wake_child_stderr`, keeping at most 1024 bytes, and copies a
`Self-route:` tail onto the event. Empty stderr adds no event. The holder
does not also append that line itself. Death recovery does not wait for
the child and still discards the child's stderr. It sets
`KAOLA_DELEGATOR_WAKE_EVENT_LOG` to the dead holder's `events.jsonl`, and
the child appends the same kind of line there. That line has no EventLog
cursor. It is still a readable record.

A deliver whose `project` is not an existing directory writes no receipts
file. `status --project` cannot read one: it refuses a missing directory.
The record is that stderr line (`project-unresolved`). When a holder is
the parent, the same instruction is an event: `delegator_wake_child_stderr`
when the child started, or `delegator_wake_spawn_failed` with that
self-route when the project directory was already gone and the child could
not start. Read the holder event log. Run `delegator-webhook test` in the
project's current directory. If test delivers, continue the inquiry now.
Do not start a second Host for the missing directory.

Config lives at `~/.config/kaola/delegator-webhook.json` (override with
`KAOLA_DELEGATOR_WEBHOOK_CONFIG`, for tests). The directory is created 0700 and the
file 0600 atomically under `<config>.lock`; a config readable by group/other or not
owned by the uid is refused as `config-mode`. Keys are `os.path.realpath(--project)`:

```json
{"schema": "kaola-delegator-webhook/1", "projects": {"<realpath>": {"url": "https://...",
 "sender_key": "...", "sender_key_attachment": {...}, "enabled": true,
 "owner_agent": "<label>", "updated_at": "<UTC Z>"}}}
```

`url` requires `https://`; `http://` is accepted only for a loopback host
(127.0.0.1, ::1, localhost). `sender_key_attachment` is owner-verified configured
data: take the exact format from the Grok Bot routine panel — no header name is
hard-coded. `{"style": "header", "name": NAME, "prefix": TEXT}` sends the request
header `NAME: <prefix><sender_key>` (NAME must be an RFC7230 token and not
Host/Content-Type/Content-Length/Connection/Transfer-Encoding; the sender key is
required, non-empty, no CR/LF/NUL). `{"style": "url"}` means the key is already in
the URL and `sender_key` stays null.
Owner-verified for Grok Bot (live, 2026-10-10): routine webhooks authenticate
with `Authorization: Bearer <key>` — configure with
`--key-header Authorization --key-prefix 'Bearer '`; a bare key without the
prefix gets HTTP 401.

CLI (`scripts/kaola-acp.py delegator-webhook <action>`, one JSON receipt on stdout,
exit 0 on success):

- `configure --project ROOT --owner-agent LABEL` plus exactly one secret input —
  `--url-env NAME [--key-env NAME]` (values read from the named variables, never
  argv), `--stdin` or `--input-file PATH` (one `{"url","sender_key"}` object; the
  file must be a regular file owned by the caller with no group/other bits) or,
  on a TTY with no source, masked `getpass` prompts — plus exactly one attachment
  flag, `--key-header NAME [--key-prefix TEXT]` or `--key-in-url`. An existing
  entry owned by another label is refused (`entry-owned-by-other-agent`) unless
  `--replace-owner OLD` names it exactly; the same owner reconfigures freely, and
  other projects' entries are preserved. No input source on a non-TTY is
  `input-required`.
- `status --project ROOT` prints `kaola-delegator-webhook-status/1`: project,
  config_path, config_mode, configured, enabled, owner_agent,
  sender_key_attachment (style/name/prefix), sender_key_present, a 12-hex
  `fingerprint` of url+key, last_receipt, last_test, receipts_path,
  `repeated_failure`, `previous_repeated_failure`, `failed_receipts_kept`, and
  `holder_lost`. Never the URL or key. `repeated_failure` is the run above,
  or null when none is stored. `holder_lost` is `{scan, leg, wakes}`
  and, when `scan` is `skipped` or `incomplete`, `reason`. `leg` is
  `delegator-webhook status`. `scan` is `complete`, `incomplete`, or
  `skipped`. An incomplete record-root scan has `reason`
  `record-root-mismatch` and the self-route above. Each wake is
  `{session, holder_instance_id, delegator_death_wake}`. A `sent: false`
  death wake on that object carries `route` or `self_route`. `holder_lost`
  also carries `record_lost` (`{scan, lost}`) when the scan runs: the
  host-registry cross-check (#359) above. Exit stays 0.
  Eligibility, the skipped-scan rule, and the cron cadence bound are in the
  death-recovery paragraphs above.
- `test --project ROOT` sends one `state: "test"` payload through the same
  delivery path and prints `kaola-delegator-webhook-test/1` with the attempt
  receipts; exit 0 only on `delivered`.
- `remove --project ROOT --owner-agent LABEL` deletes only the caller's own
  entry; an absent entry is `result: "absent"` (exit 0).
- `deliver` is the holder's internal entry: one payload object on stdin, config
  lookup by `realpath(payload.project)`, deliver, write receipts, exit.

The Delegator records the wake pair in `timer_owner`: `wake_mode` is `heartbeat`
or `webhook+heartbeat` (absent means heartbeat-only) and `webhook_routine_id`
names the webhook routine. The payload is a signal, not evidence: on a wake the
Delegator re-reads the bridge Accepted line, locates, and reads authoritative
`status`, `observe` and `capture` receipts. Running Host holders need a seat
restart to pick up holder gating. The holder is in the operator restart set.
The #311 `status` scan lives in `scripts/kaola-acp.py`, which is outside that
set. A running holder still emits `holder_lost` only on its next `start` or
dead-holder `stop`. Between those calls, the cron `status` leg is the
detector, after the Delegator reloads the Skill that tells the inquiry to
run `status`.

## Runner entrypoint (`kaola-tmux.sh`)

The file keeps its historical name; it drives ACP only and starts no tmux session.

```text
scripts/kaola-tmux.sh PLATFORM preflight --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM start     --repo ABS_PATH --session NAME [--continue | --resume ID] \
  [--tier default|PLATFORM_TIER] [--model ID --effort low|medium|high|xhigh|max] [--fast on|off]
scripts/kaola-tmux.sh PLATFORM observe   --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM status    --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM capture   --repo ABS_PATH --session NAME [--lines N]
scripts/kaola-tmux.sh PLATFORM send      --repo ABS_PATH --session NAME \
  [--if-snapshot ID] [--text TEXT] [--wait | --no-wait] [--git-facts | --no-git-facts]
scripts/kaola-tmux.sh PLATFORM steer     --repo ABS_PATH --session NAME --text TEXT \
  [--steer-mode native|interrupt] [--git-facts | --no-git-facts]
scripts/kaola-tmux.sh PLATFORM key       --repo ABS_PATH --session NAME \
  [--if-snapshot ID] --key NAME
scripts/kaola-tmux.sh PLATFORM answer    --repo ABS_PATH --session NAME \
  [--decision-id ID] [--if-snapshot ID] --replace-editor [--text TEXT]
scripts/kaola-tmux.sh PLATFORM stop      --repo ABS_PATH --session NAME \
  [--if-snapshot ID] [--force] [--preserve-dispatched-workers]
```

`--preserve-dispatched-workers` (also on `drain-restart`) asks the stop to keep the
complete process tree (holder, native agent, tools) of each Runner session this seat
started, proven by its spawn line or a live worker record naming this exact holder as
`dispatcher`, on a cooperative stop and on dead-holder cleanup; other recorded
children are still swept. A Host or Sideagent keeps them with or without the flag:
stopping or replacing the dispatcher never ends a verified Runner session — each seat
has its own exact stop (#361). A live holder that does not advertise
`preserve-dispatched/1` returns `{"result":"refused","reason":"preserve-unsupported"}`
with `mutation_status: not_started`. The successor Host then runs `rebind-host` per
seat; a start still in flight is not covered and needs reconciliation.

ACP records default to `/tmp/kaola-<uid>` and new admin sockets to
`/tmp/kaola-<uid>-acp`; caller `TMPDIR` and `XDG_RUNTIME_DIR` do not change
these defaults. Exact-session reads, `list`, locator worker receipts and
Host uniqueness include bounded legacy-root discovery. Existing records and
their applied socket paths stay readable in place. Explicit `--record-root`
or `KAOLA_ACP_RECORD_ROOT` scope record readers; Host uniqueness still checks
other live holder roots. Ambiguous live records or unavailable legacy-root
visibility produce `record-root-mismatch`, never a false absence receipt.
See [record/socket roots](architecture.md#acp-record-and-socket-roots) for
lookup boundaries and recovery of stopped custom-root records.

Runner start and holder construction create the selected record root with mode
`0700`, verify with `lstat` that it is a directory owned by the caller, and
reject symlinked, non-directory or foreign-owned roots as `record-root-unsafe`
before writing session data. Owned roots with broader permissions are tightened
to `0700` through a verified directory descriptor. Session directories are also
created/opened without following symlinks. Legacy discovery remains read-only;
status/list/locate do not change old root permissions.

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

`--expected-holder-instance-id ID` binds `send`, `steer` (native and `--steer-mode interrupt`), `permit`,
`cancel`, `key`, and `stop` to one ACP holder instance. A mismatch returns `{"error":{"code":"holder-instance-mismatch"}}` with
`mutation_performed: false` and changes nothing, so a same-named session rebuilt by a later holder
is never stopped in place of the one the Agent verified. A `stop` whose holder pid is already dead
uses that same receipt (`expected_holder_instance_id`, `holder_instance_id`,
`mutation_status: not_started`) and writes one `holder_instance_mismatch` event; the record and
processes stay unchanged. A matching id, or no expected id, still sweeps that dead holder's
identity-verified recorded groups without `--force`. `steer` forwards only an explicitly supplied binding; it
does not bind itself from the record, and `op_steer`/`op_steer_interrupt` check it before any steer write or
cancel. The interrupt composite's follow-up prompt carries the same verified holder id.

`send` preserves omitted wait selection through `runtime-tmux.sh`, `kaola-tmux.sh`,
and direct `kaola-acp.py`. Explicit `--wait` blocks and `--no-wait` returns admission;
when both are supplied, the last wins. Omission remains blocking except when the
existing caller `KAOLA_ACP_DISPATCHER`, live Host record (`session_role: host`, or an
absent/null role with the existing standard Host `host_class` derivation),
and target worker record prove the same repo, exact owning Host instance, and matching
worker dispatcher/heartbeat binding. That default returns admission and pins the prompt
to the recorded worker holder with the existing expected-holder guard. It reads existing
records and socket existence only; it does not probe the Host or read its heartbeat file.
The receipt adds `wait_selection` with `wait`, `source` (`explicit`, `owning-host-default`,
or `standalone-default`), and a `detail` for blocking fallback. Issue #386 follows that same
resolved wait for the receipt's Git facts: a blocking send keeps `git`, a `--no-wait` send
omits it unless `--git-facts` is supplied. The legacy role fallback
does not rewrite records or infer ownership from names: exact identity and bindings still
must match. An explicit non-Host or unknown role, a missing dispatcher, missing sockets,
and ambiguous or foreign evidence keep blocking;
this creates no refusal or permission decision. A Host still explicitly sends `--no-wait`
for every assignment and ends its turn; see the existing
[Host dispatch procedure](../skills/kaola-project-runner/references/zcode-host-dispatch.md).

Executable overrides are `GROK_BIN`, `CLAUDE_BIN`, `OPENCODE_BIN`, `KIMI_BIN`,
`CURSOR_AGENT_BIN`, `DEVIN_BIN`, and `DROID_BIN` (read by `preflight` for the runtime version
fact). The entrypoint's test/embedding override is `PYTHON_BIN`.

## Transport selection

ACP is the only transport (Issue #130). `--transport acp` is accepted as a no-op; `--transport pty` on any command is refused from the arguments alone, before the manifest, Git, the canonical-root binding (#73), or the dispatcher checks (#104) are read, and before any process, holder, record, or session exists. The refusal is one JSON line on stdout, exit 1:

```json
{"schema_version":3,"result":"refused","reason":"transport-pty-retired","action":"<command>","platform":"<id>","session":"<name>","repo":"<as given or empty>","detail":"PTY transport is retired (Issue #130); this Runner is ACP-only. Re-run without --transport (or with --transport acp).","mutation_performed":false,"mutation_status":"not_started","transport":{"requested":"pty","supported":["acp"]}}
```

Any other `--transport` value exits 1 with `--transport must be acp` on stderr. Every command dispatches to `kaola-acp.py`, and every schema-3 receipt's `transport` block is `{"selected":"acp"}` plus the ACP probe facts where a command adds them; the former `default`, `alternatives`, and `reason` keys are removed and `schema_version` stays 3. ACP supports `preflight`, `start`, `send`, `steer`, `wait`, `observe`, `capture`, `permit`, `cancel`, `stop`, `view`, and local `follow`; an ordinary `capture` receipt (`--lines`, `--since`, `--tools`) is bounded to `capture_receipt_bytes` by dropping its oldest `events`/`tool_calls` and adding `truncated` (`list`, `kept`, `dropped`, `total`, `stream_bytes`, `stream_sha256` of the untruncated one-JSON-line-per-entry stream, `hint`), while `capture --full` is the explicit unbounded request; `--model`, `--effort`, and `--fast` map through the manifest config-option IDs and apply in model → effort → Fast order. For Claude Code's vendored bridge a `permit` answer settles only the reported `tool_call` status (the `claude -p` child takes no `--permission-prompt-tool`, so it cannot gate or resume the child). `permit` / `cancel` / `stop` settle each permission `request_id` at most once (same holder lock as prompt admission); a second settler on that id is `error.code` `unknown-request` and does not write another JSON-RPC result to agent stdin. Each holder process mints an opaque random `holder_instance_id` at construction — immutable for that process, never restored from `record.json` or the native session id, never derived from the PID — and exposes it on `record.json`, `status`/`observe`/`start` receipts, `kaola-acp-list/1` rows, and top-level on every `kaola-acp-view/1` payload (view plus follow snapshot/delta/heartbeat). `permit`, `cancel`, and the `key escape`→cancel alias accept optional `--expected-holder-instance-id VALUE`; when supplied — including an explicit empty value — the holder compares it against its own id under the settlement lock before any permission settlement, pending-permission cancellation, turn mutation, or outbound cancel, even when no permission/turn is active. A mismatch returns `error.code` `holder-instance-mismatch` with `expected_holder_instance_id` and the actual `holder_instance_id` inside the error object plus top-level `mutation_status` `not_started` and `mutation_performed` `false`; nothing is written to the agent. Omitting the flag keeps legacy unbound behavior. The binding is Runner envelope only and is never forwarded into native ACP method params.

Permission wakes (Issue #92): a `permission_required` event raised while its bound Host
is not listening is not lost. The worker holds one undelivered wake per pending request
and re-offers the same event from its existing watchdog tick until its Host takes it —
in-memory, no second ledger, no new scheduler, no give-up window; the wake is dropped the
moment the request stops being answerable. The wake is only a locator: the Host re-reads
the worker's live `pending_permissions` and approves nothing from the event itself, and
`permit` on the request id is the one settlement.

Codex `--permission-mode` values are literal upstream IDs, and their semantics are the upstream adapter's. On the paired pin codex-acp 2.0.0 / `@openai/codex` 0.158.0 (live-verified Issue #226), ACP passes the ID through to the `mode` config option: `read-only` is display name "Read-only" (readOnly sandbox, on-request approval; a write needs an explicit client approval), `workspace-write` is "Workspace access" (workspace writes without a prompt), `agent` is "Auto review" (auto_review), and `agent-full-access` is "Full access". The Runner's mode config option is the sandbox the turn uses. `session/new` `modes.currentModeId` stays the adapter default `agent` until `session/set_mode`; it is not the applied config option. Start receipts surface the adapter's own display names/descriptions as factual evidence in `configured_options[*].option_name` / `option_description` / `value_name` / `value_description` when the adapter returns them.

ACP `observe`/`status` report `session_meta.configOptions` as the latest native-attested option list, not the launch snapshot. The `session/new`/`session/resume`/`session/load` result is the baseline (also surfaced as `initial_config_options`); a successful `session/set_config_option` result replaces the list wholesale, and `config_option_update` notifications for the same session refresh it. `configured_options[*].current_value` carries the adapter's native `currentValue` when returned — proof is the native response, never the requested value. Failed or timed-out updates and responses without usable config facts leave the last proven configuration untouched.

`session_meta.models.currentModelId` and `initial_config_options` are both `session/new` snapshots, not the current selection: a later `session/set_config_option` never refreshes either one. Read `session_meta.configOptions[model].currentValue` (`status`/`observe`) or `effective_selection.effective_model` (`start`) instead (Issue #183).

Protocol limitation (ACP 0.225.1): the protocol shows which model is *selected*, but it carries no per-turn usage or model attribution, so it cannot prove which model *served* a turn. The selection is nonetheless stable once set — in the Issue #183 probe, one `session/set_config_option model=auto` echoed `auto` on every later `config_option_update` across the following prompts, with no revert.

The ZCode adapter (Issue #62) reports three separately trackable session identities: the Runner session name (on every receipt), the ACP session id, and the native `sess_*` id. Once a backend session is materialized or faithfully resumed the adapter emits one credential-free `session/update {sessionUpdate: native_session_identity, acpSessionId, nativeSessionId}` notification, and `session/load` returns the adopted `sessionId` plus its `configOptions` so the holder's record and every receipt track which native session was loaded. Nested Host→Worker isolation is a process/session contract (separate process groups, separate record roots; the outer exact stop sweeps recorded inner sessions); the explicit runtime facts `KAOLA_ZCODE_ENTRY`/`KAOLA_ZCODE_NODE` are forwarded to a nested ZCode child, while the holder's `KAOLA_ACP_CHILD_RECORD` write handle and the denied credential names are never forwarded. See [ZCode host](zcode-host.md).

Human watch is not an L0 receipt. `kaola-acp list [--platform P] [--repo ROOT]` and `kaola-acp survey` (below) are the only commands without a required platform positional or `--repo`; stdout is one `kaola-acp-list/1` object of live holders; `--include-dead` (Issue #132) adds records whose holder PID is gone. Each row also carries `identity` (`verified` | `dead` | `unreachable` | `mismatch`: record, live PID, answering admin socket, and a `state` reply whose `holder_instance_id` equals the record's, probed with a 5 s bound), `host_class` (the standard Host name `<platform>-<CODE>-orchestrator-<purpose>`), `dispatcher` (the dispatching holder identity the holder inherited from `KAOLA_ACP_DISPATCHER`, or `null`), and the binding fact `heartbeat_host` / `heartbeat_host_known`. `kaola-acp <platform> view --repo ROOT --session NAME [--since CURSOR]` stdout is one `kaola-acp-view/1` object. Its timing and permission-outcome fields (Issue #257) are holder-clock facts in Unix seconds with millisecond precision; ACP itself carries no timestamps. Each `messages[]` entry has `received_at` (float | null): the holder receipt time of the message's first chunk, equal to that chunk's `events.jsonl` `ts`, and `null` for the prompt message the holder itself wrote (that message has no event-log line). `turn` adds `started_at` (the time the holder wrote the `session/prompt` frame, the record's `last_prompt.written_at`) and `ended_at` (the `ts` of the `turn_ended` event, or of `process_exited` when the agent died mid-turn), each `null` while unknown. Issue #381: `turn`, `event_cursor` and the projection's turn rows are copied under one leaf holder lock, so one payload never mixes a terminal `turn` with the previous live cursor and never reports `active: true` without its `started_at`. For a started turn (`started_at` non-null), a terminal `turn` carries the cursor of its ending `turn_ended`/`process_exited` event (or a newer cursor from later events); a prompt frame written before an agent exit is published as `process_exited` on that exit's cursor. A no-write admission failure (`pending_out` missing) legitimately reports `turn_failed` with no ending event because that turn never started. `turns[]` lists every prompt turn this holder process wrote, oldest first and capped at 200: `{started_at, ended_at, outcome, stop_reason, start_cursor, end_cursor, clientMessageId?}`, where `start_cursor` is the turn's prompt-message `cursor` and `end_cursor` the ending event's cursor, so a message whose `cursor` falls in `[start_cursor, end_cursor]` belongs to that turn. `answered_permissions[]` lists, in answer order and capped at 200, every permission answer the Runner wrote to the agent (`permit`, plus the `cancelled` answer `cancel`/`stop` writes for a pending request): `{request_id, title, tool_call_id, options, chosen_option, outcome, answered_at, cursor}`. `options` matches `pending_permissions[].options`; `chosen_option` is `{optionId, name, kind}` (only `optionId` set when the agent never offered that id) or `null` for `cancelled`; `outcome` is `approved` for an `allow_*` kind, `denied` for a `reject_*` kind, `cancelled`, or `unknown` for any other kind; `answered_at` is when the answer was written (for `permit`, the `permission_answered` event `ts`); `cursor` is the newest event cursor at that moment. A request the agent withdrew (`$/cancel_request`) or that vanished with the agent was not answered by the Runner and is not listed. These lists live in the holder's in-memory projection and start empty when a holder restarts; a dropped turn or answer sets `truncated`. Issue #380: a prompt admitted with `--client-message-id` carries the same value on its `messages[]` user row and its `turns[]` row as `clientMessageId`; a prompt without one omits the key on both, so the pre-#380 shape is unchanged. The view schema is not bumped (additive optional field). Terminal and command output bodies are not added: they already arrive as tool `content`. `kaola-acp <platform> follow --repo ROOT --session NAME [--since CURSOR] [--format text]` keeps the Unix socket open and writes NDJSON `{kind:snapshot|delta|heartbeat|eof|error}` lines; snapshot/delta payloads reuse `kaola-acp-view/1`. After the first `follow` op that FD is read-only (`prompt`/`permit`/`cancel`/`stop` reply `kind=error` and must use another short connection). A slow follower whose queue exceeds 256 lines gets `follow-dropped` and disconnects; other followers, `view`, and agent stdio continue. Killing the follow CLI does not stop holder/agent. Agent exit emits `kind=eof`, after which the holder closes that connection and the CLI exits; a dead holder emits `kind=error` `holder-lost`. View caps are enforced, not only flagged: thinking keeps an 8 KiB tail, one tool's content is clipped to 32 KiB, the timeline keeps the newest 200 messages, and a view over 256 KiB drops its oldest tools, then oldest messages, answered permissions, and turns. Issue #384 adds disclosure without adding a delta or a replay: `messages_dropped` is the integer count of message rows omitted from `messages[]` by the timeline and byte caps; `earliest_cursor` is the first cursor in the returned `messages[]` (`null` when empty); `truncation.rows.messages.timeline` and `.bytes` each carry `{dropped, reason}` (`timeline-cap`, `view-bytes`); `.restart` carries `{dropped, reason, boundary_cursor}`; `dropped` is `0` with `boundary_cursor:null` for a holder with no prior event history, and `null` only when the process began against a positive historical cursor. In that case prompt admission has no complete prompt text or uniform prompt-turn-start rebuild evidence (some agent-initiated turns do record `turn_started`), so the exact lost row count is unknowable and no replay is attempted. `truncation.rows` also counts dropped tool cards, turns and answered permissions, and `truncation.event_log` reports `{gap, reason, oldest_cursor}`. `truncated_event_log` and `truncated_rows` split the two classes, but `truncated` remains the union of all previous cap signals (including the thinking tail and per-tool content clipping, which the two new booleans do not cover) plus those two classes; it is not `truncated_event_log || truncated_rows`. `cursor_gap` is true when `--since` is below the oldest retained event cursor or below the earliest cursor this payload can describe completely across every row class (dropped message rows, tool cards, turns or answered permissions; `cursor_gap_reasons` lists `event-log` and/or `rows`); without `--since` it is false, but the row-loss fields still disclose what the compacted view cannot carry. The view schema is not bumped (additive fields). Chunks without `messageId` join the previous same-role message until a tool call, new prompt, or turn end, except that a prompt-sourced row is never extended (Issue #385). `--format text` joins message/tool titles into tty text (not a TUI). Runtime facts use `error.code` in `holder-lost` / `holder-unreachable` / `no-session`. `kaola-tmux.sh PLATFORM view` prints `{"error":{"code":"view-unsupported","message":"view is not a Runner command; use kaola-acp"},"schema":"kaola-acp-view/1"}`, exit 1; `follow` is likewise `follow-unsupported` (`"kind":"error"`). `install-local.sh --bin-links` (default on for the Codex runtime destination) also installs owned `$HOME/.local/bin/kaola-acp`, `kaola-acp-holder`, and `kaola-project-runner-locate` symlinks.

### User-echo dedupe (Issue #385)

`user_message_chunk` is an echo only when its whitespace-normalized text (every whitespace run
collapsed, case and punctuation preserved) matches the current prompt's normalized fingerprint.
`messageId` is not an exemption: an echo with one is dropped exactly like an echo without one. Only
the current prompt participates; when a newer prompt is admitted, the previous prompt becomes
history and a chunk equal to it is no longer dropped. The former exact-or-substring test is gone, so
a chunk that merely contains the prompt (or is a substring of it) is never consumed.

A logical user message is judged as a whole, not chunk by chunk. While its accumulated normalized
text is a proper prefix of the current prompt it is held; when it exactly equals the prompt it is
held as a matched echo. A later chunk may keep it a prefix, complete it, extend it, or prove it
different. A whitespace-only chunk after a complete match remains part of that echo (the normalized
message is unchanged) and is dropped at its boundary. A chunk that extends or diverges publishes the
**entire accumulated text** as one user row; later chunks for that message append to that row and are
never compared with the prompt again, so changing the split point cannot drop real text. A
proper-prefix probe that meets a boundary without completing becomes its own user row; a complete
echo is dropped at that boundary. A later chunk after the boundary is handled under the existing
chunk-continuity rules. The prompt's own `messages[]` row is internally marked and is never
extended by a chunk; an unknown non-echo chunk opens or joins an ordinary non-prompt row. The
`messageId`/`clientMessageId` identity on those rows is unchanged.

The prompt identity and the chunk classification are read under the same projection lock that
admits a prompt, and the holder passes the raw prompt fingerprint of the turn the update arrived
under; a prompt admitted between receipt and classification cannot re-key an in-flight echo. The
event log is not filtered: `events.jsonl` still records every `session_update`, echo included, for
Issue #384 replay/audit. The dedupe is projection-only, and the view schema is not bumped.

### Per-turn thinking projection (Issue #382)

`view.thinking` belongs to the turn that is open, not to the holder's lifetime. The holder resets
`chars`, `text_tail` and `messageId` when a real prompt is admitted (after this holder's
`session/prompt` frame is written) and when an agent-initiated synthetic turn opens (#341). It does
not reset at turn end: a completed, cancelled or failed turn keeps its last thought readable until
the next turn opens.

Steering follows the same boundary. A native `steer` writes into the running turn and opens no
turn, and an idle `steer` is never written, so neither resets the block. A
`steer --delivery after-turn` waits for the finished turn and then uses ordinary prompt admission,
so the reset happens at that admission. `steer_interrupt` cancels and sends the steering text as a
new prompt turn, so it resets at that admission too. A refused prompt (busy turn, holder mismatch,
client-id replay or conflict, stopping holder, no ACP session, or a frame that was not written)
never resets, because the reset runs only inside the admission of a turn this holder actually
wrote.

Known limitation: ACP `session/update` carries no turn id, so the holder cannot attribute a late
`agent_thought_chunk` to the turn that produced it. A thought from an ended or cancelled turn that
arrives after the next turn has opened is applied to that open turn, and can restore its old
`messageId`. Thinking is therefore reset at each turn boundary, not strictly attributed per turn;
a consumer that folds one Thinking row per turn should use its own turn boundary rather than
`messageId`. Scoping by the holder-local `turn_request_id` was rejected because that id never
appears on the wire and cannot distinguish the chunks.

The block is in-memory only: a holder restart or ACP resume starts empty, and `record.json` keeps
only per-turn `thinking_chars`, never the text or the message id.

### Issue-name advisory (Issue #313)

`start` and `list` add an advisory for issue-named worker sessions. The field is
`issue_name`. Its only values are `ok`, `malformed`, `platform-token-mismatch`, and
`no-active-run`. The command does not refuse, rename, or restart a session because of
this field. The 1-80 `--session` syntax remains the only name validator. There is no
registry and no new Workflow state field.

`ok` means the session name is `<exact-platform-id>-<CODE>-i<ISSUE>-<purpose>` and
the repo's main checkout has exactly one in-progress, non-bundle
`kaola-workflow/<run>/workflow-state.md` whose `status` is `active`, whose
`issue_number` is that issue, and whose `claim_repository_id` has the same git
origin as the session repo. `CODE` starts with a letter and is letters and digits
only. The exact platform id is required, character for character. It is the
manifest `id` derived from `platforms/*.yaml` `session_prefix` by removing the
`-kaola` suffix (`claude-code`, `cursor-cli`, ...). A short alias does not count:
`claude-PROJ-i123-x` on platform `claude-code` is `platform-token-mismatch`, and
`cursor-` on `cursor-cli` is the same class. Another platform's prefix is the same
class. `malformed` means the name has no `i<ISSUE>` field or does not parse, and it
is not a host, sideagent, seat, or general name (`claude-PROJ-haiku-1749-x`, and a
leading-digit code such as `codex-1KT-i1-work`). `no-active-run` means the name
parses and that scan did not find exactly one non-bundle same-origin run
(`grok-PROJ-i123-x` with no active run for issue 123, two active runs, a bundle
run, or a different origin). Same origin is the same GitHub `owner/repo`,
case-insensitively, or the same origin string when it is not a GitHub URL. A
bundle run has a `bundle_id`, more than one `issue_numbers` value, or a `bundle-`
folder name.

`issue_name` `ok` uses that same exactly-one rule. The field is optional and
additive on `kaola-acp-list/1` rows. The schema name stays `kaola-acp-list/1`.
No existing list field is removed or renamed. The four `issue_name` strings stay
`ok`, `malformed`, `platform-token-mismatch`, and `no-active-run`. The join rule
and the representative names are
`tests/contract/kaola-terminal-name-contract.json`, stated in
`docs/issue-dispatch-display.md`. A null `agent_alive` on a list row stays
unknown. It is not ended.

A host name (`<platform>-<CODE>-orchestrator-<purpose>`), a `sideagent` or legacy
`sidekick` name, a `seat` name, or a general name
(`<platform>-<CODE>-general-<purpose>`) omits `issue_name`. The receipt sets
`name_role` to `host`, `sideagent`, `seat`, or `general` instead. That marker is
not `session_role` and it does not change seat accounting. Host, sideagent, and
general names carry no `i<ISSUE>`, and this advisory draws no task progress for
them. An issue-named worker sets `name_role` to `worker` next to `issue_name`.
`list` puts the same fields on each row.

The lookup reads `kaola-workflow/<run>/workflow-state.md` in the main checkout only
(one directory level; `archive` is not a run). It reads `status`, `issue_number`, and
`claim_repository_id` from that file. The folder name is not a claim. `kaola-acp.py`
is a per-call CLI. A running holder does not gain this field until the next `start`
or `list` process. Existing sessions are left as they are.

### Seat issue drift (Issue #312)

`project --seats` (`kaola-dispatch-seats/1`) and the Delegator seat summary report
`issue_drift`. The list is always present. It is empty when nothing drifted or when
the session-name helper is not beside `kaola-dispatch.py`. The field is computed when
the view is read. It is not written into the index, the live list, the heartbeat
file, or a registry. `execute` does not refuse because of it. `state check` `ok`
does not flip because of it. The holder and the injected heartbeat body still have
no seat table.

A row is one live seat. Stopped seats, the Host, and the bound Sideagent are not
rows. `advisories` is `dispatch-issue-mismatch`, `no-active-run`, or both, with
the mismatch first. `dispatch-issue-mismatch` means the session name yielded an
issue and a current dispatch issue differs from it. A current dispatch item is
`in-flight` or `unknown`, or `returned` while acceptance is not `accepted`,
`cancelled`, `superseded`, or `handed-off`. An item that names a different
`holder_instance_id` is not this seat's item. `no-active-run` is the same fact as
`issue_name` `no-active-run`: the name classifies `ok` and that issue does not
have exactly one non-bundle same-origin run. A short alias keeps its start
advisory and is not also called `no-active-run` here. A name that does not yield
an issue is not a drift row. A matching name and dispatch issue with that one
run is not a row.

`name_issue` is the issue in the session name. `dispatch_issue` is that one
current issue, or null when the seat has none or several. Several current issues
also set `dispatch_issues` to those integers, sorted. `suggestion` is:

```text
At the next safe point, exact-stop this seat and start a fresh standard-named session. Never retarget this live seat to another issue.
```

The same advisory object is `issue_drift` on that session row and, when the seat
is occupied, on its occupied row. The suggestion is the next safe point. The view
does not exact-stop, rename, or retarget the live seat.

```json
{"advisories": ["dispatch-issue-mismatch"], "dispatch_issue": 1758, "holder_instance_id": "h1", "name_issue": 1720, "platform": "codex", "session": "codex-PROJ-i1720-work", "suggestion": "At the next safe point, exact-stop this seat and start a fresh standard-named session. Never retarget this live seat to another issue."}
```

### Session role

`session_role` (Issue #245) is one additive session identity on the holder record and on `list`, `status`/`observe`, and `view`/`follow`. Known values are `host`, `sideagent`, `expert`, `elite`, and `worker`. JSON `null` means the identity is not established. A legacy record that lacks the key is the same as `null`; nothing rewrites or restarts that seat to fill it. `host_class` stays the boolean name-pattern fact (`<platform>-<CODE>-orchestrator-<purpose>`, with the existing `-i<digits>-` worker exclusion) and is not replaced by this field.

Derivation, in order: a standard Host name is `host` (authoritative; `session_role` mirrors `host_class`). An explicit start `--role sideagent` — the current role flag — is `sideagent`. `expert`, `elite`, and `worker` come only from the preset this start actually selected (`selection_basis.preset_id`) and that tier's manifest `{tier}_model_class`, lowercased. A custom `--model`, a resume that preserves the native session without the same-native-session inheritance identity, an unknown class, or missing evidence is `null`. Session-name spelling, model-id substrings, session purpose, and an unrelated default preset are not evidence. Unknown is never labeled `worker`.

`list` projects `session_role` as `host` when `host_class` is true, otherwise the persisted record value, otherwise `null`. That is the consumer fallback for a legacy Host row: `host_class` true still reads as Host even when the stored field is missing. `status` and `observe` lift the persisted value to the top level next to `start_evidence` (a live state reply already carries it; a missing or unknown stored value is `null`). `view` and `follow` (snapshot, delta, and heartbeat) pass the holder value through. A live holder whose `session_role` is `sideagent` or legacy `sidekick` does not occupy a worker seat or a shared seat group (Issue #303). The bound Sideagent node is recognized by that role: the record has no separate node flag. The bound maintenance session's plan item is `seat_exempt: true`. A plan item with role `sideagent` that is not that bound session is still counted as a worker when admitted (`evidence.seat_note`). A live worker (`expert`, `elite`, `worker`, or no role) still occupies, and a `shared-occupied` refusal names that occupant. A dispatch plan `role` of `sideagent` is passed as start `--role sideagent` and kept on the index for correlation. Apart from the legacy alias below, other `role` values stay index metadata: it does not authorize that role, relabel a holder, or refuse the item. The seat's `session_role` still comes from the Host name, that explicit sideagent flag, or the selected preset Class. Recovery does not re-send or change a live session's role; a persisted-versus-requested sideagent mismatch is a note only.

Legacy `sidekick` remains accepted in start flags and dispatch plans and stays
verbatim in existing holder records, receipts and indexes. Consumers render both
`sideagent` and `sidekick` as Sideagent. Recovery treats them as the same role
without relabeling a live session, replaying work or renaming any session. No
schema version changes. New callers use `sideagent`; unknown values still stay
unknown.

A native model component `role` (`main` or `sidekick` inside `model_display.components`) is a Fusion composition fact, not `session_role`.

Installed platforms are a separate host-wide fact (Issue #147). `kaola-acp survey [--platform P] [--login-shell SHELL]` is read-only: it starts no agent, opens no ACP session, creates no holder, record, or record root, runs no platform binary (not even `--version`), and so spends no model turn. Its only child process is one non-interactive login shell (`SHELL -l -c`, stdin closed, bounded to 10 s and killed as a group on timeout), started from a fresh minimal environment (`HOME`, `SHELL`, `PATH=/usr/bin:/bin:/usr/sbin:/sbin`, `TERM=dumb`, plus `USER`/`LOGNAME`/`TMPDIR`/`LANG` when set), that prints its environment; the shell is `--login-shell`, else the account's login shell, else `$SHELL`, else `/bin/zsh`. A client with a narrow PATH (a GUI app subprocess) therefore sees what a new login sees. A `.zshrc`-only PATH edit is interactive-only and is not part of the login environment. Stdout is one `kaola-acp-survey/1` object, exit 0: `{schema, login_env, platforms}`. `login_env` is `{shell, shell_source: argument|account|SHELL|default, status: ok|unavailable, detail, path}` (`path` is the login PATH, `detail` says why it is unavailable). `platforms` has one row per platform in Runner order (`claude-code`, `codex`, `cursor-cli`, `devin`, `droid`, `dsh`, `grok`, `kimi-cli`, `opencode`, `zcode`; `--platform` keeps one), every row with the same keys: `platform`, `runtime_name`, `status` (`present` | `absent` | `unknown`), `installed` (`status == present`), `path` (the resolved executable or `null`), `source`, `binary`, `binary_env`, `requires_env`, `process_path`, and `login_path` (the manifest `binary_name` resolved on the invoking PATH and on the login PATH, each an executable path or `null`). `source` follows the Runner's launch order: `binary_env` (the manifest override in the invoking environment), `process_path`, `login_binary_env` (the same override exported by the login shell), then `login_path`. `absent` means neither environment resolves it; `unknown` means the invoking environment does not and the login environment could not be read, so absence is not established. ZCode keeps its launch rule: `binary` and `binary_env` are `null`, `requires_env` is `["KAOLA_ZCODE_ENTRY", "KAOLA_ZCODE_NODE"]`, and the row is `present` (`source` `process_env` or `login_env`, `path` the entry) only when both are absolute paths to an existing entry file and an executable runtime in one environment; a `zcode` on PATH or an installed application bundle is not probed. OpenCode Go is a provider route inside the `opencode` and `dsh` CLIs, not a separate binary, so those two rows carry it. `install-local.sh --bin-links` exposes the survey as `$HOME/.local/bin/kaola-acp survey`.

Quota packages are a separate read-only catalog (Issue #148). `kaola-acp packages [--platform P] [--installed-only] [--login-shell SHELL]` and `kaola-acp model-package --platform P --model ID` start no agent, open no session, create no holder or record, and spend no quota. Login environment is not required. `--installed-only` reuses the survey and keeps platforms whose `status` is `present`; only that flag runs the login shell. Stdout is one JSON object with sorted keys, exit 0. `packages` is `kaola-acp-packages/1`: `{schema, installed_only, platforms}` plus `login_env` only when `--installed-only`. Each platform row is `{platform, packages:[{id, name, windows, binds_models}]}` plus `pool` when the package declares a shared pool. `id` is `<platform>:<token>`; a package may carry `pool` (a bare token) naming the provider-side shared quota pool its usage counts against — Issue #368 merges Grok and Cursor usage into one shared pool `cursor-grok` that each runtime reads through its own acquisition with no cross-mapping. `cursor-cli` declares `cursor-cli:account` and `grok` declares `grok:account`, both named `Cursor+Grok account usage` with window `monthly` and `pool: "cursor-grok"`; the old `cursor-cli:cursor-models`/`cursor-cli:other-models` split and its `explicit` map are removed. A model still resolves to its own runtime's package id — grok models never resolve to `cursor-cli:account` or the reverse — while the emitted `quotaPool` names the shared pool `cursor-grok` on both platforms, so Delegator and Host views present one shared line. The Cursor runtime reads Cursor usage itself and needs no Grok install; the Grok runtime reads Grok billing itself; neither acquisition reads, mirrors, or derives from the other. A stored or stale `quotaPool` value is never read back — every emission re-derives it, and an installed copy still carrying the old catalog reports `stale` until its seat restarts. `windows` remains null or an array of strings: current values are `5h`, `weekly`, and `monthly`; multiple known periods can be listed together. An empty array means the package is verified to have no time-based reset window; null means the package-level period is not established. This field names confirmed reset periods only, not quota amounts or reset timestamps; an unlisted period is not proven absent unless the provider documents the complete set. Antigravity (`antigravity:account`, Issue #329) lists `5h` and `weekly`, verified live on `agy 1.3.5` via `agy -p /usage --output-format json` (`kaola-quota.py` `parse_antigravity_usage` / `probe_antigravity_usage`, which normalizes `Gemini Models` (`gemini-weekly`, `gemini-5h`) for both verified tiers `antigravity/default` (`gemini-4-argon-medium`) and `antigravity/xhigh` (`gemini-4-argon-high`) and `Claude and GPT models` (`3p-weekly`, `3p-5h`) into `used`/`limit`/`used_percent`/`remaining_percent`/`remaining_fraction`/`reset_at`/`window`). Factory's Individual Plans docs specify three rolling windows (5-hour, 7-day, and 30-day) for individual-plan Standard Usage. Droid Standard therefore lists `5h`, `weekly`, and `monthly`. Droid Core is a separate Rate Limit pool after Standard Usage is exhausted; the docs do not specify Core window periods, so the catalog keeps only the owner-confirmed weekly and monthly periods for Core and does not infer a 5h window ([Factory Individual Plans](https://docs.factory.ai/pricing/individuals)). Kimi exposes both `kimi-cli:managed` (weekly and monthly) and the additive `kimi-cli:managed_monthly` (monthly only); Kimi model identifiers expose the same `kimi-code` prefix for both plans, so the new variant does not bind models and consumers need account-plan context to select it. Droid `extra_usage` uses an empty window list because Factory describes its prepaid credits as non-expiring (same source). Current unresolved package periods remain null for `claude-code:extra_usage` (the supplied facts establish subscription periods, not this extra-usage balance), `devin:overage` (no period is established for this separate overage entry), and `opencode:zen` (no Zen-specific period is established; the OpenCode Go fact does not cover it). `model-package` is `kaola-acp-model-package/1`: `{schema, platform, model, packageId, status}` plus `pool` when the resolved package declares one, where `status` is `mapped` or `unmapped` and `packageId` is the qualified id or null. A usage error exits 2. An id with no verified rule is unmapped, never a guessed package. A static query (no live row) may still map an owner-confirmed preset id through the manifest's static preset map, and a live row's present native field value still wins over that static map. Example, mapped: `{"model": "grok-4.7", "packageId": "grok:account", "platform": "grok", "pool": "cursor-grok", "schema": "kaola-acp-model-package/1", "status": "mapped"}`. Example, unmapped: `{"model": "brand-new-model", "packageId": null, "platform": "droid", "schema": "kaola-acp-model-package/1", "status": "unmapped"}`. `observe`/`status` stamp model leaves on the emitted receipt only (`quotaPool` shared-pool id when the package declares `pool`, else the qualified id, or `quotaPool` null and `quotaPoolStatus` `unmapped`). `view` adds `models.availableModels` and `models.options` (the model config option only) from a copy. Stored `session_meta` and `record.json` stay the native ACP payload. The installed Project Runner reference `references/quota-packages.md` keeps the seat-failure rule only. For display, show the weekly or monthly window when the plan has one; show the 5h window only when it has neither.

One platform:

```json
{"installed_only": false, "platforms": [{"packages": [{"binds_models": true, "id": "grok:account", "name": "Cursor+Grok account usage", "pool": "cursor-grok", "windows": ["monthly"]}], "platform": "grok"}], "schema": "kaola-acp-packages/1"}
```

A platform with several packages:

```json
{"installed_only": false, "platforms": [{"packages": [{"binds_models": true, "id": "droid:standard", "name": "Standard", "windows": ["5h", "weekly", "monthly"]}, {"binds_models": true, "id": "droid:core", "name": "Core", "windows": ["weekly", "monthly"]}, {"binds_models": true, "id": "droid:extra_usage", "name": "Extra usage", "windows": []}], "platform": "droid"}], "schema": "kaola-acp-packages/1"}
```

### Command Code live usage (`dsh:commandcode`)

Issue #347. KaolaTerminal reads one stdout JSON object from:

```bash
python3 scripts/kaola-quota.py --platform dsh --model commandcode/deepseek/deepseek-v4.1-flash --probe
```

Exit code is 0 for `ok`, `key_missing`, `unavailable`, and `error`. The same process exit stays 0 for a catalog query with no `--probe`, and for `--probe` on any other platform or model (that result stays `usage.status: "unsupported"`). `--timeout` is seconds for each HTTP attempt (default 20). There is one attempt per route and no retry.

The probe runs only when the model resolves to `dsh:commandcode`. `commandcode/...` on `dsh` is that package. `opencode-go/...` resolves to `dsh:opencode-go` or `opencode:opencode-go` and is not queried, mixed, or summed with Command Code. `--platform opencode --model commandcode/...` stays unmapped.

Stdout shape (catalog fields unchanged, then `usage`):

```json
{
  "platform": "dsh",
  "packages": [],
  "resolved": {"packageId": "dsh:commandcode", "status": "mapped"},
  "usage": {
    "platform": "dsh",
    "packageId": "dsh:commandcode",
    "provider": "commandcode",
    "status": "ok",
    "model": "commandcode/deepseek/deepseek-v4.1-flash",
    "quota": {"window": "5h", "used": 9, "limit": 10, "used_percent": 90.0, "remaining_percent": 10.0, "remaining_fraction": 0.1, "used_fraction": 0.9, "reset_at": "2025-10-21T01:35:54Z", "exceeded": false},
    "windows": {
      "5h": {},
      "weekly": {},
      "monthly": {}
    },
    "credits": {"monthly": 40, "purchased": 3, "free": 1},
    "plan": {"id": "individual-goat", "period_end": "2026-11-17T15:23:56Z"},
    "period": {"spend": 1.25, "requests": 5, "tokens": 40345}
  }
}
```

`usage.status` is `ok`, `key_missing`, `unavailable`, or `error`. Every non-ok object has `quota: null`, `windows: {}`, a short `reason`, and no `credits`, `plan`, or `period`.

| status | reason | when |
| --- | --- | --- |
| `key_missing` | `COMMANDCODE_API_KEY is not set` | the named key is absent |
| `unavailable` | `http 401`, `http 403`, `http 404`, `http 410`, `http 429`, `http <5xx>` | that status on `GET /alpha/billing/credits` |
| `unavailable` | `upgrade_required` | HTTP 403 whose `error`, `code`, `type`, `reason`, or `message` is exactly `upgrade_required` (Go plan) |
| `unavailable` | `timeout` | the credits request exceeds `--timeout` |
| `unavailable` | `network failure` | the credits host cannot be reached |
| `unavailable` | `response shape changed` | HTTP 200 without a `windowLimits` object, or without a usable `fiveHour` or `weekly` window |
| `error` | `probe failed` | an unexpected local failure; the exception text is discarded |

`quota` is the window with the smallest `remaining_fraction`. Windows with a null fraction are not candidates. Equal fractions break ties in order `5h`, `weekly`, `monthly`.

A limit window (`5h` from `windowLimits.fiveHour`, `weekly` from `windowLimits.weekly`) copies `used` and `cap` as `used` and `limit` (absolute credits, not a percent). `exceeded` is the boolean on that window. `remaining_fraction` is `clamp((limit - used) / limit, 0, 1)` when `limit > 0`, and `used_fraction` is `1 - remaining_fraction`. `used_percent` and `remaining_percent` are those fractions times 100, rounded to two places, the same rounding as the Antigravity normalizer. `reset_at` is `windowLimits.*.resetAt` (epoch milliseconds) rendered as UTC `YYYY-MM-DDTHH:MM:SSZ`, the Antigravity `reset_at` form. `0`, a missing value, and a number below `1e11` are `null`.

`credits.monthly` / `purchased` / `free` are `credits.monthlyCredits` / `purchasedCredits` / `freeCredits`. The `monthly` window's remaining balance is `credits.monthly`. Its `limit` is the subscription grant when that lookup returns HTTP 200, otherwise `null`. A numeric `grant`, `creditGrant`, `includedCredits`, `monthlyGrant`, or `planCredits` on the subscription object is that grant. Otherwise a known `planId` uses the published plan grant below. Any other id, or a failed lookup, leaves `limit` null. The probe does not invent a limit from the remaining balance. When `limit` is null, monthly `used`, percents, and fraction are null. When both are known, `used` is `max(0, limit - remaining)` and `reset_at` is the billing period end in the same UTC form.

| planId | monthly limit |
| --- | --- |
| `individual-go` | 10 |
| `individual-goat` | 70 |
| `individual-pro-v1` | 80 |
| `individual-max` | 150 |
| `individual-ultra` | 300 |
| `teams-pro` | 40 |

Those amounts are the published Command Code usage-limits table (Go, GOAT, Pro, Max 10×, Max 20×, Team Pro) for the `planId` spellings the subscriptions route returns.

`plan` is present only when the subscription lookup returns a plan id or period end: `{"id","period_end"}`. `period` is present only when `GET /alpha/usage/summary` returns numbers: `spend` is `totalCost`, `requests` is `totalCount`, `tokens` is `totalTokens`. A failed subscription or summary omits that object and does not change `status`.

Routes, each `GET` with `Authorization: Bearer <COMMANDCODE_API_KEY>` and one attempt: `/alpha/billing/credits` (required), `/alpha/billing/subscriptions`, `/alpha/usage/summary`. The probe does not call `/alpha/whoami`. It copies only the fields named above and drops every other key, including `email`, user id, org id, price id, and subscription id, before anything is returned. It does not print, log, cache, or write the key or the raw response.

The key is read by name at probe time: process environment `COMMANDCODE_API_KEY`, then `$DSH_HOME/.env` (or `~/.dsh/.env` when `DSH_HOME` is unset), then `.credentials.yaml` `refs.COMMANDCODE_API_KEY`. A set `DSH_HOME` does not fall back to `~/.dsh`. An empty value is missing. A missing key is `key_missing`, not an exception.

### Cursor+Grok shared pool live usage (`cursor-grok`)

Issue #368. Each runtime reads the shared pool through its own acquisition;
neither calls, mirrors, nor derives from the other, and each keeps its own
`packageId` while reporting the same `pool` (`cursor-grok`):

```bash
python3 scripts/kaola-quota.py --platform cursor-cli --probe
python3 scripts/kaola-quota.py --platform grok --probe
```

The Cursor acquisition is `GET $CURSOR_API_ENDPOINT/auth/usage` (default
`https://api2.cursor.sh`), `Authorization: Bearer` a Cursor `API Key` read at
probe time from `CURSOR_API_KEY`, then `~/.cursor/.env`, then the `refs` map
of `~/.cursor/.credentials.yaml` (the installed Cursor CLI's keychain entry
is its canonical macOS credential; the file surfaces let automation inject a
key deterministically). `used` sums the per-model `numRequests` buckets,
`limit` is `maxRequestUsage`, and `reset_at` is the first instant of the
month after `startOfMonth`.

The Grok acquisition is `GET $GROK_WEB_BASE_URL/billing?format=credits`
(default `https://code.grok.com`), `Authorization: Bearer` a Grok key read at
probe time from `GROK_API_KEY`, then `~/.grok/.env` (or `$GROK_HOME`), then
the `key` recorded by `grok login` in `~/.grok/auth.json`, preferring an
unexpired `expires_at` entry. `used`/`limit`/`used_percent` come from
`includedUsed`, `monthlyLimit`, and `creditUsagePercent`, and `reset_at` is
`currentPeriod.end` (epoch milliseconds) in UTC form.

Both normalize into the same envelope (`pool`, `packageId`, `quota{window,
used, limit, used_percent, remaining_percent, reset_at, ...}`), so with both
available the two readings of the shared pool agree. The Cursor reading
needs no Grok install or credential; with every Grok credential surface
absent the Grok probe reports `key_missing` while the Cursor probe still
returns `ok`. The failure vocabulary extends the Command Code one
(`key_missing`, `unavailable`, `error`; `reason` names the cause) with
`login_required` for a 401/403 rejection. Neither probe spawns a
CLI binary, starts a session or seat, or writes a usage record.

## Tool cwd watch (#369, #373)

The holder records its own agent's tool-shell working directory before a removal can take it,
repairs a vanished one, notices the agent, and cleans up. The fact is `record.json`'s
`tool_cwd`: `{last_known, source: trace|note|process|null, observed_at, exists,
placeholder: [PATH, ...], notice: none|pending|delivered, notice_paths: [PATH, ...],
notice_ts: STAMP|null, repairs}`.
`placeholder` is a set, so several removed worktrees keep their own claims (N-1).
`status`/`observe` carry it (`tool_cwd`) and every current repair duty
(`tool_cwd_errors`: a list of `{code, path, message, route}`, so simultaneous duties all stay
visible); `list` rows carry `tool_cwd_path` and `tool_cwd_exists`, plus `agent_pid`,
`agent_pgid` and `agent_child_pgids` for the cwd guard's process trees. A resume restores
`tool_cwd` from the previous record; a fresh start inherits only the placeholder claims, never a
stale `last_known` (R2-1). Either boot reconciles each claim against the filesystem and
`git worktree list`: exists + empty + unregistered stays, a registered or non-empty claim is
dropped, and an unreadable list keeps the claim and records `cwd-unverifiable` (R2-2).

The manifest fields are `shell_cwd_persistence` (`persistent|per-call|unknown`; absent =
unknown), `tool_cwd_note_regex` (one named `path` group; absent = no in-band carrier), and
`tool_shell` (`zsh|bash`; absent = tier A off). Recording tiers:

- **A — runner-owned shell entry (#373).** When `tool_shell` is set, the holder exports
  `KAOLA_TOOL_CWD_FILE=<record_dir>/tool-cwd` and either `ZDOTDIR=<record_dir>/shellenv`
  (zsh) or `BASH_ENV=<record_dir>/shellenv/.bashenv` (bash) to its agent process. The
  runner-owned entry writes `$PWD` once per top-level tool shell, guarded by
  `KAOLA_TOOL_CWD_TRACED` so nested shells skip, then restores the user's own
  `ZDOTDIR`/`BASH_ENV` and sources that init, so the user's shell setup is unchanged.
  The holder reads the file on every execute-kind `tool_call`, at turn end and on the status
  scan; a file older than the agent start is ignored. A failed (`ENOENT`) spawn writes nothing,
  so the file keeps the dangling path V1 needs. ZCode is on (`platforms/zcode.yaml`
  `tool_shell: "zsh"`); its adapter forwards only these tier A names into the app-server, and
  only when the holder set `KAOLA_TOOL_CWD_FILE`. Tools that spawn `/bin/sh` (or another shell
  without an entry hook) get no tier A record and stay on tiers B/C.
- **B — in-band note.** `tool_cwd_note_regex` applied to
  `tool_call`/`tool_call_update` `content` text only (zcode's measured Read note).
- **C — live shell sample.** One rate-limited (`2 s`) cwd sample over the agent's own child
  processes on an execute-kind `tool_call`. It accepts only a descendant whose `exe_basename`
  is a shell (`zsh`, `bash`, `sh`, `dash`, `fish`, ...); an adapter or other non-shell process
  is no observation at all.

Observations are last-write by their own `observed_at`: a tier A record carries the entry
file's mtime, so a newer tier A path beats an older tier C sample and a tier C sample can never
overwrite a fresher tier A path; equal timestamps prefer trace over note over process.

Signals: **V1** a recorded path that no longer exists; **V2** a registered worktree path that
disappeared from `git -C REPO worktree list --porcelain`, refreshed at holder boot, turn end, on
execute-kind events and on the status tick (with `shell_cwd_persistence` not `per-call`, an
unknown `last_known` gets a pre-emptive placeholder); the refresh stays off the prompt path
because the prompt path already holds `worker_events_lock`, which a staged notice also takes;
**V3** `spawn <shell> ENOENT` while that shell exists, or
`chdir|getcwd|shell-init ... No such file`, in `content`. V3 with no recorded path leaves the
`tool-cwd-unknown` duty in `tool_cwd_errors` instead of a silent no-op.

Repair: one placeholder per occurrence, coalesced on the path, and only inside the repo, never
the repo root, never a registered worktree (`os.makedirs`), and never for a path that still
exists. A worktree list that cannot answer is recorded as `cwd-unverifiable` (probe `git`),
creates nothing and keeps an existing claim. Repeated status ticks of the same missing path
record one vanish event (N-2). The notice is fixed text naming the repaired path(s) and the repo
root, stamped once per batch in `notice_ts` (cleared when that batch is delivered). A retry
reuses the stored stamp, so the text and its `steer_fingerprint` do not churn. One notice batch
is staged for the whole repair set, so one steer names every repaired path in that batch; a
`host_owned` worker event `kind: cwd_repaired` is staged per repaired path. It steers when the
turn is active and the manifest declares `native_steering: supported`, otherwise the event batch
is delivered as one self prompt at the next idle boundary. A receipt of `injected`, or of
`written`/`queued` with `mutation_performed: true` (dsh's native steer answers `written`), is
delivery once for that turn: the notice becomes `delivered` and is not steered again. Even when a
receipt cannot be marked as delivery, one `turn.request_id` never steers the same `notice_paths`
batch twice; the notice then stays `pending` and rides the next boundary's self prompt. The
payload follows the holder's own `session_role` (#388): only a `host` holder gets the Host
carrier (`kaola-host-notify/1` with `host_skill_entry` and the heartbeat body); a worker,
Expert or Sideagent holder gets the compact `kaola-worker-notify/1` notice carrying only the
structured event lines, even when an older start passed it a Host entry. An
undelivered notice stays `pending`, is visible in `status`, and is retried at every later
boundary; a V2 pre-emption while the shell cwd is unobserved stages a new batch, which gets its
own steer (the delivered batch is not re-sent). A placeholder is removed (`os.rmdir`, empty only)
once the reported cwd is outside it
or at `op_stop`; a path that became a registered worktree again is dropped and left alone; a
non-empty one is left and reported as `cwd-placeholder-not-empty`. Events:
`tool_cwd_observed`, `tool_cwd_vanished`, `tool_cwd_unknown`, `tool_cwd_unverifiable`,
`tool_cwd_trace_failed`, `tool_cwd_placeholder_created`,
`tool_cwd_notice_staged|delivered`, `tool_cwd_placeholder_removed|left`,
`tool_cwd_repair_failed`.

## Post-compaction Skill reread

The holder reads completed compaction signals for its exact ACP session through the pinned
`kaola-compact-recovery.py` helper. Supported carriers are `compaction_update`, OpenCode's
completed `_meta["opencode/compaction"]`, Devin and Grok native notifications, and Kimi's exact
four-line completed text. The Claude bridge forwards a native `compact_boundary` with object
metadata; the ZCode bridge maps its native completed compact events. Start, failure, cancel,
foreign-session and startup history signals do not trigger a reminder. Kimi's wire does not
mark the text as runtime-local; identical model text can cause a harmless reminder.

The holder uses its existing prompt path at a turn boundary. A Host uses its measured entry;
a worker reads its current installed platform Skill and active role/task Skills, then continues
its task. The current Codex native recovery path owns that behavior, so the holder sends no
second prompt and adds no compaction capability to initialize. This does not establish native
automatic recovery for every runtime.

`compact_reload_detected` records recognition. `compact_reload_delivered` records admission of
the reminder prompt, not a full Skill read or task use. Confirm those actions from the actual
model output and tool evidence. A duplicate of the current pending occurrence id coalesces
without advancing its sequence. A boolean guards admission. Settlement and release of that
guard share the existing lock; the pending sequence preserves a newer signal even when both
events have no occurrence id. One pending reminder is kept in memory, with no history or queue.
It is lost on stop. Running holders keep their loaded code; older holders need a later
Agent-selected start to use the new behavior. No session restart is performed by this mechanism.


### Opt-in Droid/Cursor project precompact notice

`scripts/kaola-project-compact-notice.py --binding ABS_FILE` is an optional native project
hook command. It reads the native hook input on stdin. It sends a KPR `compact_notice`
operation to the existing holder socket. This is a KPR local extension, not a vendor ACP
method. Project configuration and the binding are Agent-selected; no hook is installed by
start, render or the helper. Default transport and native Codex recovery stay unchanged.

For Droid 0.233.0, use only the supported project `PreCompact` command hook. The native
session id equals the ACP id. A standalone root uses `ROOT/.factory/hooks.json`; a Git root
can change this lookup. Do not set `FACTORY_HOME_OVERRIDE`, move auth or bypass trust. Stop
can follow errors and is not a success signal. For Cursor 2026.09.28-64d2043, use project
`preCompact` under the ACP data project `G/.cursor/hooks.json`. Its hook resource puts the
ACP id in `conversation_id` and normalizes `session_id`. Bind the exact `workspace_roots:[G]`.
General `CURSOR_CONFIG_DIR` does not move native user hooks; effective native policy still applies.

The binding names `platform`, `socket_path`, `holder_instance_id`, `acp_session_id`,
`project_root`, `platform_skill_path` and nonempty `task_skill_paths`. Cursor also needs
`hook_project_root`. All Skill files must exist at full absolute paths. The owner must select
current installed applicable files; file existence alone does not prove applicability or reading.
The helper forwards only selected identity fields. It rejects conflicting native session ids,
foreign roots, missing identities and unsupported events. It reads the holder's current request
id, then the holder checks it under its existing lock. No shared unknown-session fallback is used.

A valid notice stages one obligation in the existing compact tracker during the exact active
request. Duplicate notices for that request coalesce. It does not call compaction completed or
send another prompt while the original request is active. The original request must end with
`turn_completed`, `end_turn` and no observed error. Standard prompt admission checks the same
holder, session, prior request and successful outcome under its normal admission lock. An
intervening request, refusal, failure, cancel, stop or dead agent leaves the obligation pending.
A newer request's notice cannot replace an unresolved prior notice. The owner reconciles such a
result from the existing record/events; it is not a new notice admission.

The reminder says completion is unconfirmed, requires full current applicable installed Skill
reads through the file read tool, then task continuation. Hosts retain their measured entry;
workers receive no Host entry. `compact_project_notice` records the notice;
`compact_project_notice_admitted` records a later standard ACP prompt admission with read/use
unverified. `state.compact_project_notice` exposes a pending target and unknown-write fact.
Unknown/partial writes are retained without automatic replay. The hook client does not retry a
lost socket reply and does not block native compaction. Reconcile original effects before any
retry. One in-memory obligation is lost on holder stop; existing receipts remain the recovery
source. This route adds no file watcher, polling service, scheduler, history or exactly-once gate.
Actual hook invocation, full file reads and resumed-task results require separate live evidence.

## Observation schema

`observe` returns evidence for the controlling agent. ACP `observe`/`status` receipts are bounded by `bound_state_receipt`
in `kaola-acp.py`, on their own `state_receipt_bytes` budget (256 KiB, Issue #64:
a realistic platform `session_meta` — Devin's is ~70 KB — and the stored `record`
(~142 KB) stay whole, so `session_meta.configOptions` `currentValue` remains readable;
only larger structures are summarised) (`record`, `initial_config_options`, `session_meta`, `capabilities`,
`agent_info` summarised by size and sha256; `pending_permissions` keeps its newest entries).
Only `capture --full` is unbounded. Every schema-3 receipt carries `platform`, `session`, `repo`
and `transport`. Git reporting facts (`git`, `{branch, dirty}`) are command-scoped since Issue #386:
`send --no-wait`, `steer` and `permit` omit `git` by default and do not run the Git probes; a `send`
whose resolved wait is blocking (including explicit `--wait`) keeps it, as do `status`, `observe`,
`start` and the other schema-3 receipts. `--git-facts` or `--no-git-facts` overrides the default for
one invocation (the last flag wins; `kaola-tmux.sh` forwards both). These facts are evidence for the
controlling agent and never semantic authority for `send`/`stop`.

ACP receipts also report the notification binding in force (Issue #70). `start`, `observe`
and `status` carry `heartbeat_host`: the target the running holder really adopted, or `null`
for an ordinary unbound worker; a holder or record written before the field exists instead
answers `heartbeat_host_known: false` (unknown, never reported as unbound), and a receipt with
no session at all stays silent. `start` keeps what it asked for separately in
`heartbeat_host_requested`, and a `session-exists` start reports the reused holder's binding,
so a later environment change or a repeated `start` can never look like a rebinding.

`rebind-host` (Issue #255) is the one in-place carrier change. Run from inside a live Host
session against an existing seat, it derives the target from that Host's own
`KAOLA_ACP_DISPATCHER`, checks the record is a Host-role, live, same-instance holder with its
socket, and sends the holder op `rebind_heartbeat_host`. The receipt carries `rebound`,
`previous_heartbeat_host`, `heartbeat_host`, `dispatcher`, and the unchanged
`holder_instance_id`; the seat logs `heartbeat_host_rebound` with both dispatcher values.
Refusals are `{"result":"refused","reason":"rebind-host-unresolved"}`
exit 1 before the seat is touched, and holder errors `no-heartbeat-host` (seat started unbound),
`missing-host-holder-instance-id`, `heartbeat-host-foreign-repo`, or `holder-instance-mismatch`.
A holder that predates the op
answers `unknown-op`; that seat recovers through `drain-restart` as before. A Sideagent whose
own record names no Host now dispatches through the ordinary dispatcher rows. `rebind-host`
moves only the target seat's carrier: the seat's `dispatcher` is rewritten to the replacement
Host (`platform`, `session`, `repo`, `holder_instance_id`), so the new Host counts it as a live
seat and its sends prove ownership; every
seat (the Sideagent included) needs its own call, and worker events staged in a Host holder that
died are not moved; the new Host adopts them from the index and receipts.

Sideagent relay (`sideagent-relay/1`): a Host holder relays routine worker events (from any
session but the Sideagent's own) to the bound Sideagent's live holder. Each relay round trip
(connect, send, every read) shares one 1 s deadline, so a slow or trickling Sideagent cannot
hold the event lock; a miss returns the event to the Host as `sideagent-unreachable`. The
Sideagent may already have admitted that prompt, so the Host can see it as well (at-least-once).
The relay mark keeps the Sideagent's `dispatch_event_cursor`. A Sideagent turn end is settled
before queue admission, so a full queue never refuses the completion that drains it: a completed
turn confirms its relays; a failed or cancelled one returns them to the Host; a later turn end
whose cursor is past a relay's cursor returns that relay as `turn-end-missing` (its own end was
lost). Each return is logged as `worker_event_relay_returned`. No timer is added.

When a Sideagent holder stops (cooperatively or by `stop --force` after holder loss), it spares
the whole process tree of every worker it dispatched. A worker counts as dispatched by it through
its spawn line in `children.jsonl` or through its own live record: `dispatcher.holder_instance_id`
equal to the Sideagent holder's, with the record's `holder_pid` running as a `kaola-acp-holder`
under that record directory. The second source covers the ZCode bridge, which forwards no
`KAOLA_ACP_CHILD_RECORD`. A foreign record, a wrong `holder_pid`, or a reused spawn line protects
nothing.

A `start` receipt also says where its request came from (Issue #104): `heartbeat_host_source` is
`none` (no dispatching holder, no variable), `explicit` (`KAOLA_ACP_HEARTBEAT_HOST` given),
`dispatcher` (derived from the holder-set `KAOLA_ACP_DISPATCHER` identity fact: `holder_instance_id`,
`platform`, `repo`, `session`, echoed as `dispatcher`), or `dispatcher-no-carrier` (a dispatcher
whose platform has no measured `host_skill_entry`; since Issue #126 admitted codex, no shipped
platform), or `dispatcher-not-host` (Issue #255: the dispatcher's own record names an established
role other than `host`, such as a worker starting sessions for its own assignment; the start is
unbound, `dispatcher` is still recorded, and that caller supervises by waiting, because a worker
woken as a carrier received full Host heartbeat passes). A holder whose role is established and
not `host` also never relays to a Sideagent or starts a maintenance node. An unknown role keeps
the earlier behaviour. Issue #122: that row, an explicit
variable naming such a platform, and a Host-named `start` on it are refused `host-entry-unsupported`
(`detail` names the platform and the empty entry), exit 1, before anything exists. On the `dispatcher` path the script verifies the named Host holder is live
before anything exists and otherwise refuses with `{"result":"refused","reason":
"heartbeat-host-unresolved"}` (`detail` names the failed check), exit 1; an explicit variable naming a
different Host than the dispatcher is `heartbeat-host-conflict`. The former #104 reason
`heartbeat-host-pty-unsupported` is retired: a `--transport pty` request is now refused
`transport-pty-retired` for every caller, ahead of these checks. Every refusal carries `mutation_performed: false`; standalone starts are unchanged.

Every platform's `start` checks, before anything is spawned, that the worker Skill copies its agent will
load are the same build as the Skill tree this CLI was loaded from (Issue #105, extended to every
platform's worker starts and to `~/.local/bin` launches by Issue #162). The Issue #104
binding lives in the copy a worker `start` executes, so a caller on a new build with an older installed
worker Skill dispatches unbound workers and exits 0. The check hashes `kaola-acp.py`,
`kaola-acp-holder.py`, `kaola-tmux.sh` (and `kaola-zcode-acp.py` where both sides ship it) in every
Skill directory under the four default ZCode discovery roots — `<repo>/.zcode/skills`,
`<repo>/.agents/skills`, `~/.zcode/skills`, `~/.agents/skills` — that contains
`scripts/kaola-acp.py`. Any difference is `{"result":"refused","reason":"worker-skill-build-skew"}`,
exit 1, nothing created; `worker_skill_skew` names the differing paths with both 12-hex digests and
`worker_skill_skew_count` the total. A passing `start` reports `worker_skill_build` (this build's
`kaola-acp.py` digest) and `worker_skill_roots` (each root and the Skill names compared), so `status`
reconciliation has the fact. Both are `null` when the CLI ran from a repository checkout rather than
an installed Skill tree or `~/.local/bin`: no Skill build to be the baseline, so the answer is unknown, not aligned.
A start whose `sys.argv[0]` lives in `~/.local/bin` uses the link target (the checkout `scripts/`) as
the baseline and compares the platform's discovery roots the same way.

`status` and `list` report `runner_build` (sha256 prefix of the holder file that seat
executes), `accepted_revision`, `stale`, `stale_reasons`, `restart_files`, and
`reported_drift` (Issue #162). `stale: true` is only the release-note restart set:
`kaola-acp-holder.py`, `kaola-zcode-acp.py`, `kaola-quota.py`, `scripts/adapters/`, and the platform
manifest (`platforms/*.yaml` or the installed `scripts/platform.yaml`), when the bytes
now at the path the seat recorded differ from the digest it captured at startup.
`reported_drift` carries the report-only drift codes; see that field for the
codes this build emits - they never set `stale`. `baseline_exempt` is recorded at start:
true only for a direct checkout invocation, which reports drift and does not block.
A start through `~/.local/bin` records false. That link resolves into the checkout,
so the resolved holder path is not the exemption. The pin is read from the registration beside `kaola-project-runner-locate`
on `PATH`, else `~/.local/bin`. `drain-restart` runs the start pre-spawn refusals
before it stops; a refusal there leaves the seat up (`mutation_performed: false`).
A refusal that still occurs after the exact-stop reports `mutation_performed: true`
and `drain_stopped`. A seat that is not idle is refused `drain-not-idle`
immediately and left running - there is no idle polling loop, so retry timing
belongs to the caller. That idle read happens only while the holder is alive: a
seat whose holder is already gone (a cleanly `stop`ped record) has nothing to
drain, so it goes straight to the start instead of being refused for idleness.
The restart carries the recorded `start_selection`
(model, effort, tier, fast, mode) unless the command passes those flags.
The recorded mode is the *effective* mode the previous start applied
(Issue #181): the platform default is resolved once, at the start that applies
it, so nothing here re-derives one. An explicit `--mode` wins over the record,
and there is no other candidate. The receipt echoes the mode the new start
actually applied, so a seat that recorded none still reports the default rather
than `null`. It refuses
`drain-restart-selection-unknown` before stopping when the seat recorded no
start selection and the command passed none of `--model/--effort/--tier/--fast/--mode`.
Adoption is a direct read of the new start's own `dispatcher`; no other seat is
scanned.
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
(Issue #198, owner-aware in Issue #215): for each affected root, the owning runtime's
`install-local.sh --runtime NAME [--platform PLATFORM]` from the accepted checkout — a root is
owned when it is that runtime's own install destination or its receipts record that runtime as a
referrer — and the generic `--skills-dir ROOT` route only where nothing owns the root, with the
matching `render-skills.py --verify-install` command for the affected set. That installer
replaces only a copy its receipt owns and keeps every other referrer; a `--skills-dir` install is
the `generic` referrer and also plans `kaola-delegator`, so where the receipt lists a runtime
referrer, that runtime's `--runtime NAME` install is the owner route and the generic route is
never presented as the owner. A root whose other Skills are also stale takes the complete-root
refresh (no `--platform`), not repeated single-platform installs. An owned obsolete duplicate is
withdrawn with the same route plus `--uninstall`, and a renamed copy no installer manages is named
for its owner to move. Nothing is deleted or retried for the caller; the refusal is pre-mutation
(`mutation_status=not_started`), so after the refresh verifies the same `start` may run again. A
Host that cannot run the authorized install itself relays this exact route to the Delegator or
operator and keeps its task and seat. `worker-skill-build-skew` names
the same per-root route with the skewed copies' platforms and `--no-orchestrator`. A passing Host `start` reports
`main_skill_build`, which is `null` when there is no record to compare (a checkout invocation or a
worker Skill built before the record). Hidden installer backups (`.${name}.drift.$$`,
`.${name}.old.$$`, `.${name}.tmp.$$`) are never installed Skills and are never compared: a start
reports them separately as `stale_install_backups` with `stale_install_backup_count`,
`stale_install_backup_roots`, and the executable `stale_install_backup_recovery` route
(`./scripts/install-local.sh --quarantine-stale-backups --skills-dir ROOT`), while a backup
present by itself never produces `worker-skill-build-skew` and never blocks `start`.

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
`--expected-holder-instance-id` against the record (`holder-instance-mismatch`, one `holder_instance_mismatch` event, record and processes unchanged),
stops a holder that answers, as the record's own instance, on the `--socket` its own argv names (a holder started under another
spelling of the same record root, e.g. `/tmp` vs `/private/tmp`, derives another socket path) with an
ordinary stop over that socket (`answering_socket`), and signals only a silent PID whose argv anchors
it to the record (`holder_force_killed`); a reused PID
gets no signal (`pid_reused: true`, `holder_signalled: false`), the dead holder's recorded groups
are swept exactly as for any dead holder (`force_killed_pids`: the agent's own process group only
while its live leader has exactly the start second the holder recorded as `agent_started` (epoch
seconds, so time zones do not matter) at spawn; plus
child groups that still match their recorded start time), and the record is retired once nothing of them is left
(later `status` reads `no-session`; a survivor keeps the record and appears in `residual_pids`). An
unreadable argv refuses `holder-unreachable`. A stop of a dead
holder, with or without `--force`, after a matching or omitted expected holder id, that leaves nothing of its recorded groups marks the record `stopped`, so `status` reads
`stopped` with `residual_pids: []`. Issue #191: macOS reuses a pgid once its group empties, so a
record written before `agent_started`, or an agent group whose leader is gone, proves no identity.
When such a recorded `agent_pgid` still has live members, either force-stop path signals none of
them, retires only this seat's `record.json` (never a newer one written in its place), and reports
`pgid_identity: "unverified"` with `pgid_identity_unverified` (`code: pgid-identity-unverified`,
`agent_pgid`, `live_members`, `signalled: false`, `retired_record`); `status` then reads
`no-session`.

### `steer` — Agent-chosen steering of a running turn (Issue #65)

`steer --repo ABS_PATH --session NAME [--text TEXT | --stdin] [--steer-mode native|interrupt]
[--timeout SECONDS] [--cancel-timeout SECONDS]` delivers one Agent-chosen message to the turn that is
**already running** on that exact session. It is a tool the controlling Agent decides to use, never a
Runner policy, and it reuses the same session/repo routing as `send`: no scheduler, no second stdin
writer, and no second lifecycle. It works over ACP, the only channel; the former
`steer-unsupported-transport` reason is retired with the PTY transport (Issue #130).

Every platform has a usable path inside ACP, and the Agent picks which one:

- `--steer-mode native` uses the platform's supported noninterrupting input entry and exists only where that entry
  really does. The manifest is the single source of truth: `native_steering` is `supported`,
  `unsupported` or `unknown` (an uninvestigated surface stays `unknown` and never masquerades as
  `unsupported`), `acp_steer_method` carries the entry and may be non-empty only when
  `native_steering` is `supported`, and `steering_summary` records the versioned evidence. Read the
  current roster out of `platforms/*.yaml` rather than from this page: which platforms qualify
  changes as surfaces are investigated, so no count or list is pinned here. The OpenCode `1.18.17` -32601 probe and `2.0.11`
  initialize observation remain historical. The V2 local adapter adds the entry for CLI 2.0.22;
  native ACP keeps the original prompt and stream. It checks the exact active ACP request id,
  then uses the installed plugin `session.prompt` API with `delivery:"steer", resume:false`.
  `native-admitted` confirms inbox admission. It does not confirm consumption or adoption.
  A turn-end race can leave input pending without starting a new turn.
  Grok CLI 1.0.46 uses `_x.ai/interject` with top-level `text`. Its nested `queued` reply
  maps to `written`, `steer_consumed:null`, and `native-queued`. This is an interject request
  acknowledgment. It does not mean admission to the holder's later-turn follow-up queue.
  Grok has no native expected-turn guard: a turn-end race can start a detached fallback turn.
  Read the original and subsequent session output before you judge processing and adoption. Never replay an unknown write.
  The new adapters and mappings require a new holder at a safe boundary. A running
  holder retains its old code. No consumer is restarted by this change. A custom `opencode acp`
  command has no adapter entry. V1 and other V2 builds are unverified.
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
| `queued` | `null` | `holder-queued` | process-local input pending until the current prompt ends; no native write yet |
| `written` | `null` | `write-only`, `native-queued` or `native-admitted` | write or native admission confirmed; processing and adoption are unconfirmed |
| `interrupted_and_resent` | `true` | `cancel-confirmed` | composite: the turn was cancelled and confirmed stopped, then this text ran as the next turn |
| `resent_without_interrupt` | `true` | `no-turn-to-interrupt` | composite: the turn had already ended on its own, so nothing was interrupted |
| `started_new_turn` | `null` | `agent-confirmed` | the agent opened a separate turn on the same session; this holder does not track that turn |
| `not_consumed` | `false` | `none` | nothing was written |
| `unsupported` | `false` | `none` | no native entry on this platform or transport |
| `rejected` | `false` | `none` | the agent refused; `error.detail` carries its reason |
| `unknown` | `null` | `none` | undecided — the Runner never resends blindly |

A native follow-up queue maps to `written`, `steer_consumed:null`,
`steer_native_outcome:queued`, and `mutation_performed:true`. Later processing needs session
output evidence. Processing can occur in the current step, a later step or a later turn.
A turn-end race alone does not make noninterrupting delivery fail. The exact session and
ongoing work must remain, with no transport cancel, stop or restart.

Devin CLI 3000.11.3 and Droid 0.233.0 use the registered `session/prompt` path.
The holder sends one additional prompt without replacing the original prompt owner.
`prompt-completed` and `steer_stop_reason` retain the additional reply. They do not
prove model adoption. A flushed frame with a pending reply maps to `written` and
`write-only`; the late `steer_reply` remains in the existing capture event log under
its own request id and the original prompt id. No timeout triggers cancel or replay.

For a native ACP route that rejects or cancels a concurrent prompt,
`steering_delivery: after-turn` holds the input in the live holder until the current
prompt ends. One operation waits on the existing completion condition. It then uses
ordinary prompt admission once. There is no timer or new scheduler. The original
prompt keeps its ended state, and the follow-up uses the normal owned prompt lifecycle.
`steer_queue_cursor` binds the queue receipt to the later `steer_followup` event and
its native write receipt. It records `original_turn` with the original id, final text and
terminal state, and a distinct follow-up id. Queue admission does not return
`turn_request_id_after` or `turn_request_id_preserved` before the native operation.
A competing prompt can refuse that write. A stopped holder
loses this process-local pending input. Read the existing events before any recovery;
never replay an unknown effect. This route cannot process input until the current prompt ends.

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

### Client message id - idempotent send/steer (Issue #380)

`send` and `steer` accept `--client-message-id ID`; every other command refuses the flag as
`{"result":"refused","reason":"invalid-input","error":{"code":"invalid-input"}}` with
`mutation_performed:false` and writes nothing. The holder validates the value: non-empty, at most
200 UTF-8 bytes, and no C0/C1 control characters; `client-message-id-empty` and
`client-message-id-invalid` are clean pre-write refusals (`not_started`, `false`).

A live holder advertises `client-message-id/1`. The CLI preflight reads the record's
`holder_features`; a live holder without the feature refuses `client-message-id-unsupported`
(`mutation_performed:false`) before any socket write, with the route "wait until idle, then
drain-restart". A dead holder keeps its ordinary transport answer.

The ledger is keyed by the id, the op, the SHA-256 text fingerprint and the ACP session id, and is
process-local, FIFO and capped at 64 entries: the 65th registration evicts the oldest id, which may
then be admitted again as a new message. A prompt performs its lookup, write and registration in
one `self.lock` admission critical section. A steer reserves a provisional entry inside that same
critical section immediately after its frame is written; a composite interrupt reserves one at
entry, before any cancel or prompt. A reservation is not yet a successful admission: the final
receipt replaces that same entry in place, so settlement never changes FIFO order, and a late final
receipt whose reservation was evicted is dropped rather than overwriting a newer admission that
reused the id. A concurrent same-id request sees the reservation in the admission critical section
and does not write a second frame.

The same id/op/text/session replays the original admission receipt with `idempotent_replay:true`,
`replay_of_turn_request_id` (the turn the original admission bound to), the original
`dispatch_event_cursor` when the admission carried one, and `holder_instance_id`;
`mutation_performed` reports the original admission's actual effect (a prompt is true; a steer keeps
its first true/false/null judgement). No second user row or turn is created. A different op, text
or ACP session is `client-message-id-conflict` (`mutation_performed:false`) and nothing is written.
A matching resend while a steer or interrupt is in flight replays a conservative `steer_in_progress`
or `steer_interrupt_in_progress` receipt with `mutation_performed:null`, and writes nothing. A clean
no-write (a busy refusal, an unsupported/rejected steer, an idle steer, or `promptRequired`)
withdraws the reservation, so the same id stays retryable; if that reservation is still the newest
entry and had displaced the oldest receipt at a full window, the receipt is restored at its
original position, so a failed placeholder never shrinks the successful window. A later
successful admission already owns the slot and is not displaced by the restore. `steer_interrupt` keeps its reservation only when
a cancel was sent or its prompt was written, replacing it with the final receipt.

The ledger is not persisted. After a holder restart, an id and text matching the recorded
`last_prompt` (`last_prompt.client_message_id` and its fingerprint) are refused
`client-message-id-restart-unknown` with `mutation_performed:false` and `previous_prompt`; the resend
is not blindly admitted. The composite checks this itself before reserving or cancelling, and its
internal follow-up prompt is not the only guard. The restart guard is deliberately narrow: the same
id with a different text, or an older id reused after a newer prompt, is a new admission. There is
no cross-restart conflict protection over the full id set. `view` echoes the value as
`clientMessageId` on that prompt's user row and turn (the key is omitted when no id was supplied),
and `record.last_prompt.client_message_id` keeps it for restart detection. Without an id the
receipt and view keep their previous shape, including `duplicate_warning` and the duplicate-turn
behaviour.


## Status compatibility

Preflight reports runtime binary/version, optional Workflow capability discovery, recurring evidence,
project materialization evidence, and an adapter-specific summary. Missing Workflow carriers,
configuration health, or materialization does not block the CLI communication channel.

Preflight also resolves the declared Runner default without starting a session. `start` gives an
explicit user model/effort precedence; otherwise `--tier NAME` selects the manifest preset
(`default` when `--tier` is omitted; other names are the platform's own `named_tiers`, see the
README table). Requesting a tier the platform does not declare, including the retired `upgrade`
or a seat record's `upgrade` carried by `drain-restart` (refused before the stop), is the typed refusal
`{"result": "refused", "reason": "tier-not-declared"}` at exit 1, naming `available_tiers`,
never a silent fallback to `default`. A bare `--model` wins over the tier preset and does not inherit
its effort; `--effort` only applies to the model selected in the same request. Model IDs that already
encode effort or Fast variants get no invented extra effort/configuration calls. `--fast` defaults to
`off`; `--fast on` is the per-run opt-in and is applied through the platform's native mechanism (Codex
ACP `fast-mode` configId, Cursor parameterized `fast` option, the Claude bridge's `fast` config option, which the
vendored bridge turns into a per-turn `--settings '{"fastMode": ...}'` — the native CLI determines model support and effective reports `unknown` without
native evidence). Where no
native mechanism or advertised fast variant exists, the request is reported `resolved_fast:
"unsupported"`, never silently claimed. `--resume`/`--continue` with `--tier` applies that
preset the same way a fresh start does (`model_selection.source` is `runner-<tier>`, and the
platform's model and effort options are sent). `--model` or `--effort` on a resume applies that
explicit selection (`source` `user`). A resume or `--continue` that passes none of `--tier`,
`--model`, or `--effort` sends no model or effort override (`resume-preserved`,
`model_selection.override_omitted` true) and keeps the saved native selection.
The omitted tier is recorded, not silent: `start_selection.tier` stays `null` and
`start_selection.tier_reason` is `resume-without-tier`; `model_selection.tier` stays `null`
and `model_selection.tier_reason` is the same word. A resume that passed `--tier` does not
set `tier_reason`. `model_selection.preserved` stays false until a fresh readback proves
continuity with the prior applied selection.
There is no automatic escalation based on complexity, failures, or elapsed time. Omitting
those flags does not by itself mean the prior applied model or effort is still in effect.
`selection_continuity` on the `start` receipt (and on `start_evidence`) is the comparison.
Its precedence is explicit current selection, then a loaded session when no prior applied
selection exists (`saved-session-selection`), then the prior successfully applied selection,
then a fresh-start default. A readback that differs from the historical applied value is not
reclassified as an intentional saved-session edit. Stale holder metadata alone never wins. A bare
continuation does not re-apply the fresh-start preset and does not overwrite the loaded session.
Explicit flags take precedence. They replace the applied baseline only when the fresh readback
verifies that explicit change.

`prior_settings_preserved` is true only when the fresh ACP `currentValue` readback matches
the prior successfully applied model and effort and the prior live readback does not
contradict them. A difference from that historical applied selection is
`differs-from-prior-applied`: not preserved, cause `unproven`, including a legacy record with
no continuity and including a difference already seen on an earlier readback. Repetition
stabilizes the observation and does not make it intentional. A missing most-recent live echo
is unknown; it does not block the continuation or add authorization. Recovery for an unproven
difference names an explicit `--model`, `--effort`, or `--tier` continuation. A missing fresh
readback is `unverifiable` and is not called preserved. Contradictory
prior applied and prior live evidence is not resolved from the stale applied value.
Recorded selection, this start's applied configuration, and the fresh readback stay
separate fields. `model_selection.override_omitted` records the no-override branch.
`model_selection.preserved` is true only when that branch's fresh readback equals the
prior applied selection. No prior applied selection, or an unreadable readback, leaves
it false. Droid's `model_verified` echo verdict is
unchanged. Catalog output is
reported as evidence and never rewrites or blocks the declared exact model literal. Actual mismatch,
catalog absence, or unreadable evidence never disables generic communication.

Model evidence under `model` on the `start`/`preflight` receipt includes `requested_model_source`,
`requested_model_name`, `requested_tier`, `requested_fast`, `requested_effort`, `model_display`,
`resolved_runtime_model_id`,
`resolved_parameters`, `resolved_fast`, and structured provenance. `actual_runtime_model_id` and
`actual_parameters` are `null` and `model_verified` is `unknown`
(`model_mismatch_reason: actual-model-evidence-not-yet-read`) on most platforms, because ACP
computes no true/false verdict from the launch request alone. Droid (Issue #185) and a Devin
default start that can read `thought_level` (Issue #342, below) are the exceptions. Droid's
selection is verified from the agent's own live current-model echo. Droid's only read-only
catalog probe is `droid --version` (no readable model catalog), and
`session_meta.models.currentModelId` is a frozen `session/new` snapshot a later set never
refreshes, so neither can verify a selection; the `config_option_update` echo is refreshed on
every accepted set, the holder mirrors it into `session_meta.configOptions[model].currentValue`,
and `start` reads that echo back through `effective_selection`. Droid's `model_verified` is
therefore `true` when the echoed model equals the resolved selection (with the echoed
`reasoning_effort` compared only when the Runner pinned an effort), `false` with
`actual-model-mismatch:<id>` when the agent reports another model, and `unknown`
(`actual-model-evidence-unreadable`, or `resume-preserved-actual-not-comparable` for a preserved
resume with no Runner target). The verdict is reported evidence, never a start gate, and
`model_evidence_provenance.actual.source` is `acp-config-echo`.
The agent's actual selection is `effective_selection` on `start`, beside
`resolved_runtime_model_id`; its `effort_config_id` names the effort option id it was read from
(the resolved `acp_effort_config_id` candidate). When the spawn argv already carries the resolved
model as `--model`, the model option is not re-sent: `config_application.model` is
`{"applied": true, "applied_via": "argv", "value": ...}` and `effective_selection.effective_model`
is that id with `effective_model_source: "launch-argv"` and `applied_via: "argv"`, the agent's own
(possibly stale) value kept as `advertised_model`. Devin ACP cannot report the argv model: its
model option ignores `--model` and need not list the preset (a `devin/default` seat advertises
`swe-2-high` while running `swe-2-max`), so for an `acp_command_<tier>` launch the argv id is
authoritative and the advertised `currentValue` is never the effective model (Issue #340).
`status`/`observe` of such a session carry the same top-level `effective_selection` (argv id as
`effective_model`, `applied_via: "argv"`, the live advertised `currentValue` — or the start's when
the holder is gone — as `advertised_model`, named by `advertised_source`).
Devin `devin/default` verifies from `thought_level` at start (Issue #342). The effort option id is
`thought_level`. The argv path does not set the model through ACP (`set_config_option
model=swe-2-max` stays rejected). It does send `thought_level` at the resolved effort (`max` for
the default preset). `effective_selection.effective_effort` is that option's `currentValue`.
`model_verified` is `true` only when `effective_model` equals the resolved model and that thought
level equals the resolved effort. `model_evidence_provenance.actual.source` is `acp-thought-level`
and `actual_runtime_model_id` is the argv model. A readable disagreement is `false`
(`actual-effort-mismatch:<value>` or `actual-model-mismatch:<id>`). A missing `thought_level`
`currentValue` leaves `model_verified` `unknown`. The advertised model `currentValue` (often
`swe-2-high`) is not compared. `opus-fusion` and `fable` keep component efforts inside the fusion
model id, declare no launch effort, and are not verified from `thought_level`. The verdict is
evidence only and does not gate the start. `status` and `observe` keep that start snapshot unless
a later runtime-model update replaces it.
On such a launch-argv start Droid's `model_verified` compares that echoed
`advertised_model`, never the argv value the Runner itself supplied, so a session whose argv model
the agent never adopted verifies `false` instead of comparing the argv value to itself.
`status`/`observe` report the
agent's own current `session_meta.configOptions[].currentValue` (raw advertised evidence; for an
argv launch read the effective model from `effective_selection`). ACP `start` receipts additionally carry
`model_selection` and per-option `config_application` receipts. When the agent rejects the resolved
model config option (`config_application.model.applied` is `false` with `error`), `start` stops the
just-created session before returning and refuses at exit 1 (`result: "refused"`,
`reason: "model-config-option-rejected"`, top-level `error` carrying the agent's `config-option-failed`
rejection and `-32602` detail, `detail` naming the option id and value, `holder_reclaimed: true`,
`mutation_status: "not_started"`), unless the caller passes `--allow-unapplied-model` to accept the
agent's own selection (`state: "ready"`, with `applied: false` and `error` kept visible in the receipt
and `status` `start_evidence`). An unadvertised option (`reason: "no-advertised-config-option"`), a
rejected effort or Fast option, and an `effective_selection` readback mismatch remain reported
limitations or evidence and leave the session usable.
When a platform advertises no effort option (`acp_effort_config_id` empty) and the accepted model
id carries the requested effort as its suffix (antigravity `gemini-4-argon-{low,medium,high}`),
`config_application.effort` is `{"applied": true, "applied_via": "model-id", "value": ...}` (Issue
#331); otherwise it stays `{"applied": false, "reason": "no-advertised-config-option", ...}`.

### Session model evidence

Issue #316. `start` still reports `model_verified: "unknown"` and
`model_mismatch_reason: actual-model-evidence-not-yet-read` unless the platform already verified
at start (Droid's echo, or Devin's `thought_level` readback, above). `status` and `observe` then read an actual model the session
already exposed. They do not write `record.json`. The on-disk `start_evidence` stays the start
snapshot. When a model is read, the status copy of `start_evidence` and four top-level fields
(`model_verified`, `model_mismatch_reason`, `actual_runtime_model_id`, `actual_parameters`)
are set from it, and `model_evidence_provenance.actual` names the read. No readable evidence
leaves those start values alone, so `actual-model-evidence-not-yet-read` stays until a read
succeeds. `configOptions.currentValue` is not that read.

The holder record wins over a new file read. A `session_update` the holder already stored
counts when it carries `_meta.runtime_model` (`id` or `model`, and `effort` when the runtime
sends one) or a Claude-shaped `message.model` plus top-level `effort`. The source is
`acp-session-update`. Prose is not scraped. `<synthetic>` is skipped. The scan is the tail of
`events.jsonl.1` and then `events.jsonl`.

Per platform:

| Platform | Actual-model evidence | When that evidence is absent |
|---|---|---|
| claude-code | Recorded session update, as above. The vendored bridge does not emit model or effort on `session/update` today, so the usual read is the session JSONL: `$CLAUDE_CONFIG_DIR` or `~/.claude`, then `projects/<cwd-with-separators-as-dashes>/<session-id>.jsonl`. The session id is the newest `native_session_identity.nativeSessionId` in that event tail, else `acp_session_id`, and only when that file exists. The last non-synthetic assistant `message.model` and top-level `effort` win (`claude-session-jsonl`). | A missing file leaves `actual-model-evidence-not-yet-read`. A file that was read and named no model is `actual-model-evidence-unreadable`. |
| droid | The start-time `acp-config-echo` verdict. A later recorded runtime model replaces it. | The echo verdict stands. Absence does not clear it. |
| codex, cursor-cli, devin, dsh, grok, kimi-cli, opencode, zcode | A recorded session-update runtime model only. Devin's launch argv and any advertised `currentValue` stay application evidence, not `model_verified`. | `unknown` / `actual-model-evidence-not-yet-read`. |

Comparison uses `model_selection.resolved_model` and, when that selection pinned an effort,
`model_selection.resolved_effort`. A match is `model_verified: true` and a null reason. A
different id is `false` and `actual-model-mismatch:<id>`. A pinned effort with no observed
effort is `unknown` and `actual-effort-evidence-unreadable`. A different effort is `false` and
`actual-effort-mismatch:<value>`. An empty resolved id on a preserved resume is `unknown` and
`resume-preserved-actual-not-comparable`, and the actual id and effort are still set, which
clears `actual-model-evidence-not-yet-read`. Any other empty resolved id is
`native-default-model-not-comparable`. No alias map is applied. Claude's preset id `opus` is
not the transcript id `claude-opus-5-5`: a `--tier default` session whose transcript says
`claude-opus-5-5` verifies `false` and still reports that id and its effort.

A preserved resume can be read on the next `status` before a new turn, because the transcript
already exists. A fresh session before its first turn has no native transcript yet, so the
reason stays `actual-model-evidence-not-yet-read`. The read is per call in `kaola-acp.py`.
The holder is not part of it.

### Consumer model name and effort

Issue #237. A downstream consumer composes its own label from a model identity and separate
effort facts. It does not parse `*_model_parameters`, a native ID suffix, or a preset label.

The preset catalog is `platforms/<id>.yaml`, copied into the worker Skill as `scripts/platform.yaml`.
For tier word `W` (`default`, or one `named_tiers` word) the prefix `w` is `W` with `-` written as `_`:

| Fact | Field |
|---|---|
| display name | `<w>_model_name` |
| native transport ID | `<w>_model_id` |
| preset launch effort | `<w>_model_effort` |
| declared components | `<w>_model_components` (optional) |

`<w>_model_id` may encode effort and stays the transport identifier. An empty `<w>_model_effort`
means this preset does not apply a separate effort option. `<w>_model_components`, when present,
is one JSON array encoded as a JSON string. Each object is `{role, name, effort}` with `role`
`main` or `sidekick` and exactly one `main`. That `main` object is the primary component.
`<w>_model_name` is the short product identity, not a join of component efforts. The field is
not copied into `<w>_model_effort`, spawn argv, or `session/set_config_option`. A fusion preset
does not publish one scalar as both components' effort.

Display names (preset IDs, profiles, classes, and quota bindings stay with these identities):
Claude Code `default` and `opus-xhigh` are both
`Opus 5.5`, with launch efforts `high` and `xhigh`. Devin `default` is `SWE-2` (main effort
`max` on the component). Devin `opus-fusion` is `Opus Fusion` (main `Opus 5.5` at `high`,
sidekick `SWE-2` at `medium`). Devin `fable` is `Fable Fusion` (main `Fable 5.1` at `high`,
sidekick `SWE-2` at `medium`). Codex `default` now selects `gpt-6.1-sol` at `high`.
Other display identities are:
`Fable`, `Sonnet`, `GPT-6.1 Sol`, `GPT-6 Astra`, `GPT-6 Luna`, `Grok 4.7`, `Claude Opus 5.5`,
`Auto Model`, `DeepSeek V4.1 Flash`, `DeepSeek V4.1 Flash (Command Code)`, `Kimi K3`, `Kimi K2.8`, `GLM 5.3`. `Flash` is the model
variant, `Auto Model` is the `auto` catalog identity, and Cursor's `Claude` prefix is the
declared family name.

On `preflight` and `start`, `model_display` is `{name, preset_id, preset_effort, components}`.
`requested_effort` is the explicit `--effort` value, or null when the flag was omitted.
`model_selection.resolved_effort` and `resolved_parameters.effort` are the launch value after
an explicit effort wins over the preset. `config_application.effort` is the apply receipt:
`applied: false` plus `error` is a rejection, and `reason: no-resolved-value` means no effort
write was attempted. `effective_selection.effective_effort` is the agent's advertised value at
that read, or null. Request and launch argv prove what was requested or applied. They do not
prove the runtime kept it. `preflight` reports `model_display` and `requested_effort` and does
not apply them; its `config_application` object is the read-only notice, not an effort result.

A direct `--model` does not select a preset. `preset_id`, `preset_effort`, and `components`
stay null, and the launch effort is only the explicit `--effort` (or none). It does not copy
the matched preset's default effort or its components. When that native ID equals one or more
declared `*_model_id` values or their `acp_model_map` wire values, and those declarations share
one non-empty `*_model_name`, `model_display.name` is that name. ZCode's provider-qualified
ID is matched by its model component, as in existing ZCode identity checks.
An ID the manifest does not declare, or one whose declarations disagree on the name, leaves
`name` null. The raw ID remains `resolved_runtime_model_id`. No suffix is stripped from an
unknown native ID to invent a name or an effort, and the tier word is not turned into a
current effort.

A preserved `--resume` or `--continue` with no new tier, model, or effort still sets
`model_display` to `{"name": null, "preset_id": null, "preset_effort": null, "components": null}`.
That invocation has no current native ID to label. `start_evidence.inherited` stays the previous
start. It is not a current observation, and its `model_display` is not copied onto this start
or onto `view.model.current`.

`status` and `observe` keep those start facts on `start_evidence` (`model_display`,
`requested_effort`, `model_selection.resolved_effort`, `config_application.effort`). That object
is the start, not a new observation. `view.model.model_display`, `requested_effort`,
`resolved_effort`, and `applied_effort` repeat that launch record. They are historical. Do not
pair `view.model.model_display.name` with a live effort.

The coherent current read is `view.model.current`:

| Field | Meaning |
|---|---|
| `native_id` | live `session_meta.configOptions[].currentValue` whose `id` is the manifest `acp_model_config_id`; null when that option or `currentValue` is missing |
| `effort` | live `currentValue` whose `id` is `start_evidence.effective_selection.effort_config_id`; the same value as `view.model.current_effort` |
| `name` | catalog label of `native_id` (the same declared mapping rule as a direct `--model`), or null |
| `name_provenance` | `catalog-declared` when `name` is set; otherwise null |

`name_provenance: catalog-declared` labels the live ID from the manifest. It does not prove a
request was applied, and it does not assign a preset. `view.models` remains the quota-stamped
available-model list. A missing option or a missing `currentValue` leaves that current field
null. Devin's live model option can still be the stale advertisement: `current.native_id` is
that advertised value, while `start_evidence.effective_selection.effective_model` stays the
launch argv and `advertised_model` stays the separate advertisement. The current read does not
replace one with the other.

Preset view, same Claude identity, distinct preset efforts (`model_display` for `--tier default`
and `--tier opus-xhigh` with no `--model` and no `--effort`):

```json
{"name": "Opus 5.5", "preset_id": "claude-code/default", "preset_effort": "high", "components": null}
{"name": "Opus 5.5", "preset_id": "claude-code/opus-xhigh", "preset_effort": "xhigh", "components": null}
```

Live receipt, `--effort low` on `claude-code/opus-xhigh`: `model_display.preset_effort` is
`xhigh`, `requested_effort` is `low`, and `model_selection.resolved_effort` is `low`. When the
agent accepts the option, `config_application.effort.applied` is true and `value` is `low`.
When the agent rejects it, `applied` is false and `error` is set, and
`effective_selection.effective_effort` is not `low`. Do not show the requested value as the
effective effort.

Unknown effort, Droid `--tier default` with no `--effort`. Show the name and an unknown effort.
Null `requested_effort` is not an effective effort:

```json
{"name": "Auto Model", "preset_id": "droid/default", "preset_effort": null, "components": null}
```

Devin `--tier fable`. Components differ. `fable_model_effort` and `acp_effort_config_id` stay
empty, so start records `config_application.effort.reason` `no-resolved-value` and does not call
`set_config_option` for effort. The argv stays
`devin acp --model fusion-claude-fable-5-1-high-sidekick-swe-2-medium`. The primary component
is `role` `main`. Do not label `high` as the sidekick effort or as `current_effort`:

```json
{"name": "Fable Fusion", "preset_id": "devin/fable", "preset_effort": null, "components": [{"role": "main", "name": "Fable 5.1", "effort": "high"}, {"role": "sidekick", "name": "SWE-2", "effort": "medium"}]}
```

Direct `--model gpt-6-luna --effort high` on Codex: `model_display.name` is `GPT-6 Luna`,
`preset_id` and `preset_effort` are null, `requested_effort` and
`model_selection.resolved_effort` are `high` (not the luna preset's `max`), and
`resolved_runtime_model_id` is `gpt-6-luna`.

Direct `--model custom-model-max`: `model_display.name` is null,
`resolved_runtime_model_id` is `custom-model-max`, and `requested_effort` is null. The `-max`
suffix is not an effort. A preserved resume uses that same null `model_display`.
`start_evidence.inherited` is the previous start.

After a launch whose `start_evidence.model_display.name` is `GPT-6.1 Sol`, a later live
`configOptions` value of `model=gpt-6-luna` and `reasoning_effort=max` leaves
`view.model.model_display.name` as `GPT-6.1 Sol` and sets:

```json
{"name": "GPT-6 Luna", "native_id": "gpt-6-luna", "effort": "max", "name_provenance": "catalog-declared"}
```

That object is `view.model.current`. A preserved resume with no live `currentValue` keeps
`view.model.current.name` null even when `start_evidence.inherited.model_display.name` is set.

Launch evidence (Issue #203). After applying the selection, `start` hands its own evidence to the
holder, which keeps it as `start_evidence` in `record.json` and every `status`/`observe` reply (from
the record when the holder is stopped or lost), across every whole-record rewrite. It is the start
receipt's `model_selection`, `model_display`, `requested_effort`, `config_application`, `effective_selection` (including
`effective_model_source: "launch-argv"` beside the separate `advertised_model`), `fast`,
`host_selection`, `model_verified`, `model_mismatch_reason`, `actual_runtime_model_id`,
`actual_parameters`, `selection_continuity`, and `model_evidence_provenance` without its `catalog_probe`, each present only
when the start receipt had it, plus `acp_session_id`, `resumed`, and `recorded_at`. It is evidence
from that start or resume, not a fresh observation: the current selection is
`session_meta.configOptions`, an applied option or launch argument is application evidence, and
only an existing verified fact (`model_verified: true`) is verified. `status` and `observe`
may overlay a live verdict onto the reported copy of `start_evidence` when session evidence
exists (Issue #316, above). The file in `record.json` stays the start snapshot. `start_selection` stays the
caller's raw flags, so an omitted `--tier` is `null`. A resume or `--continue` that also omitted
`--model` and `--effort` adds `tier_reason: "resume-without-tier"` on that object and on
`model_selection`. A resume or `--continue` whose adopted
`acp_session_id` equals the one the previous record for the same platform/session/repo ran and
recorded its evidence under keeps that evidence as `start_evidence.inherited` (`source:
"prior-holder-record"`, `holder_instance_id`, `acp_session_id`, `recorded_at`), also echoed as the
start receipt's `inherited_start_evidence`; a no-override resume (`model_selection.override_omitted`)
carries the last applied configuration forward flat, including when the fresh readback did not confirm it.
The older start's own readback stays that object's `effective_selection`, with that start's
`holder_instance_id` and `recorded_at`. `most_recent_live` is the immediately preceding holder's
native readback, checked per axis, with that holder's `holder_instance_id` and `recorded_at`.
A launch-argv model does not discard a native effort on the same object; the model axis stays
unavailable. When that holder has no native readback, `most_recent_live` is null if an older echo
would otherwise be readable, and that echo is not `prior_live`. A difference from the historical
applied selection stays `cause: unproven`. Seeing it again does not make it intentional. Explicit
flags replace the applied baseline only when the fresh readback verifies the change.
Any other native session, a Runner name alone, or a record without evidence inherits
nothing, and the model stays unknown or native-preserved. Resume sends no extra model/effort option
to fill these fields. The start receipt reports `start_evidence_recorded` (and
`start_evidence_error` when a holder could not keep it, for example a pre-#203 holder or evidence
over 16 KiB); neither is a refusal. Old records without `start_evidence` stay readable.

Droid's default is Auto Model (`auto`) with no effort pin; `--tier opus` is Opus 5.5
(`claude-opus-5-5` at `reasoning_effort=high`) and `--tier core` is Kimi K3 (`kimi-k3` at
`reasoning_effort=max`). These ids are catalog values, so `acp_model_map` stays empty. `--tier alternative` stays the typed `tier-not-declared` refusal. Its native ACP mode option is
manifest-driven as `acp_mode_config_id: autonomy_level`; the default bypass value is
`auto-high`, and there is no bridge or translator.

Claude Code's `--tier default` is Opus 5.5 (`opus`) at `effort=high` (Elite;
implementation, and the Host fallback when no tier is chosen). `--tier opus-xhigh`
is the same display name Opus 5.5, preset `claude-code/opus-xhigh`, native alias `opus` at
`effort=xhigh` (Elite; planning, design, and review; it does not perform
implementation). The preset ID is not the alias. `--tier sonnet` is Sonnet (`sonnet`)
at `effort=high` (Elite; an explicit preset and count grant, not a Worker-class preset).
`--tier haiku` is Claude Haiku (`haiku`) at `effort=high` (Worker; usable only after an explicit Worker grant).
Worker-class presets are exactly: `claude-code/haiku`, `codex/luna`, `devin/default`, `dsh/commandcode`, `dsh/default`, `opencode/default`, `zcode/default`. Each of those seven is usable only after an explicit Worker grant. `dsh/commandcode` is the Command Code DeepSeek V4.1 Flash preset in that class, and it needs a grant the same way. Codex's `--tier luna` is GPT-6 Luna (`gpt-6-luna`) at `effort=max`
(Issue #188, profile narrowed in #301): a computer-use-only Worker, not an upgrade
and not a general implementation preset. Its catalog row sets `luna_model_roles` to
`computer-use-only` (Issue #350). These are applied as ordinary ACP config
options; a native rejection is a `config_application` limitation, never a substitute.

## Agent-directed transport results

Every action goes through the exact session's ACP holder. It does not quiesce the CLI, acquire a
lease, or create a later-output barrier. `send` and `stop` do not require a snapshot; the parser
still accepts legacy `--if-snapshot` and `--replace-editor` but does not forward them. No generic
action branches on editor, activity, approval, decision, worker count, prose, Git, Workflow, or
later-output-barrier interpretations.

`send` writes the text as one `session/prompt` text block over the agent's stdio JSON-RPC, never
through a shell or a terminal, and returns `prompt_fingerprint` (`sha256:` of the text) with
`mutation_performed: true` once the frame is written; a frame that was not written is
`acp-write-failed` with `mutation_performed: false`. `start --text` or `start --stdin` uses that
same prompt path as the session's first turn (Issue #344). The receipt is a dispatch only when
`brief_delivered` is true and it carries that turn's `turn_request_id` and `prompt_fingerprint`.
`--no-wait` waits for admission (`mutation_status` `in_progress` or later), not for the turn to
end, and does not skip that check. A start with neither flag is unchanged: `ready`, no turn, and
no `prompt_fingerprint`, and that receipt is not a dispatch. An empty brief is refused
`brief-empty` before a seat exists. A brief whose turn does not verify is `brief_delivered: false`
with a typed reason and a non-zero exit, and is not a ready dispatch. `key` accepts only `escape`, which maps to
ACP `cancel`; every other key is `key-unsupported`. `answer` is `answer-unsupported` ("use send;
--decision-id maps to permit --request-id"). There is no native key, menu, or editor-replacement
transfer on ACP, and no Runner path to one since the PTY transport was retired (Issue #130).

Every `send`, `steer` and `steer_interrupt` receipt states `mutation_performed` for **that
request**, not for the previous turn. `false` means this request wrote nothing; `null` means the
outcome is unknown because the request may have been written (never resend blindly); `true` means
the frame was written. The pre-write answers `no-session`, `record-lost`,
`holder-socket-missing` and a `holder-lost` observed **before** any wire attempt report `false`
with `mutation_status: not_started`; that dead-holder form also carries the prior prompt as
`previous_prompt`, while `record.last_prompt` keeps it for `status`/`observe`. A `holder-lost`
observed only **after** a wire attempt stays unknown when it has no stage, because the frame may
have been written. `holder-closed` and a `read` stage failure report `null` with
`mutation_status: unknown`; a `connect` or `send` stage failure reports `false`/`not_started`
because the request line ends with a newline, and a failed `sendall` cannot have delivered the
complete line the holder parses. A `holder-unreachable` without a stage stays unknown because the
connect step is not proven. Issue #383 adds `error.stage` (`connect`, `send`, `read`); when
present it selects the row (connect and send are `false`, read is `null`), and a missing stage
keeps the conservative `null`. A client deadline expiry is `error.code: holder-timeout` with
`stage` and `timeout_s`; it follows the same matrix, and a prompt/steer read-stage timeout also
carries a text-free `verify` block (the request fingerprint and the `status` command that can
prove a late admission). A `prompt-in-progress` refusal reports `outcome: refused_busy`,
`mutation_performed: false`, and the active turn's `mutation_status` (not this request's). A steer
error in this class also carries `steer_outcome: not_consumed` and `steer_consumed: false` when
nothing was written, or `steer_outcome: unknown` and `steer_consumed: null` when uncertain.
`status`, `observe`, `capture`, `permit`, `cancel` and `stop` keep their existing
`holder_lost_receipt` facts; a transport timeout on `cancel`, `permit`, `stop` or `wake_delegator`
carries the same `mutation_performed`/`mutation_status` pair, while `status`/`observe`/`capture`/
`wait` never grow those keys from a failed read. A `start --text`/`--stdin` failure receipt keeps
this prompt request's mutation fact: a brief whose frame may have been written reports
`null`/`unknown`, not `false`, and that uncertain case also keeps the request's
`prompt_fingerprint` and `verify` block so a late admission can be located. A clean no-write brief
omits both, so neither can be read as a dispatch.

### Client transport bounds and timeouts (Issue #383)

`--timeout SECONDS` is the **holder-side** wait, not the client's socket deadline. The client
uses one monotonic deadline for the whole exchange: `connect`, `sendall` and every `recv`
recompute the remaining time from that one deadline and `settimeout(remaining)`. Three stages
therefore cannot accumulate three separate allowances; a 30 s bound is 30 s, not 90 s. A transport
failure without a stage keeps the conservative `null` classification; a present stage is the only
thing that proves whether the complete request line was written.

| Command / holder op | Holder-side wait | Client socket bound without `--timeout` | With `--timeout T` |
|---|---|---|---|
| `send` (resolved wait=false: `--no-wait` or owning-Host default) | admission only | **30 s** | `T + 30 s` |
| `send` (resolved wait=true: `--wait` or standalone default) | until the turn ends | **unbounded** (a real turn may run for minutes) | `T + 30 s` |
| `start --text/--stdin` brief (resolved wait=false) | same admission as `send` | **30 s**; unbounded when wait=true | `T + 30 s` |
| `steer` (native) | `T` if given, else the holder's 30 s native-steer wait | **60 s** | `T + 30 s` |
| `steer --steer-mode interrupt` | `cancel_timeout`, else `T`, else the 5 s cancel grace, then admission | **35 s** | `max(cancel_timeout, T, 5 s) + 30 s` |
| `cancel` / `key escape` | `T` if given, else the 5 s cancel grace | **35 s** | `T + 30 s` |
| `wait` | `T` if given, else until the turn ends | **unbounded** | `T + 30 s` |
| `wake` | holder wake work | unbounded (unchanged by #383) | `T + 30 s` |
| `stop` | fixed | 30 s | ignored |
| `permit` | fixed | 10 s | ignored |
| `status` / `observe` | fixed (no admission lock) | 10 s | ignored |
| `capture` / `view` | fixed (no admission lock) | 15 s | ignored |

The 30 s condition is the **resolved wait**, not the flag: a Host-dispatched `send`/start whose
`resolve_send_wait` returns `owning-host-default` is also wait=false and gets 30 s, while a
standalone `start --text` defaults to wait=true and stays unbounded. The interrupt formula is
selected by the resolved holder op (`steer_interrupt`), not by `args.command`; the CLI command
remains `steer`, but `--cancel-timeout` is still honored. The start 30 s covers only the brief
prompt socket's admission: `session/new`, model/config setup, resume waits, and the brief's
follow-up `state` probe (up to 5 s) are outside that window, so it is not a start-total wall-clock
SLA.

`--timeout 0`, a negative value, or `--timeout 0.0` is refused as a typed `invalid-input` receipt
(exit 1, `mutation_performed: false`, `mutation_status: not_started`) before any record or
transport work; `0` no longer means "unbounded". `--timeout` is accepted for legacy compatibility
on commands that ignore it (`stop`, `permit`, `status`, `observe`, `capture`, `view`), but it has
no effect there. `start`'s `--timeout` covers only the first brief prompt socket, never
`session/new`, config/resume, or the follow-up state probe.

`steer --no-wait` is a **no-op**: `--wait`/`--no-wait` is read only by `send` and `start`. A
steer's wait is the holder's native steer timeout (30 s by default), so its client bound is 60 s
without `--timeout`. The issue title's "send/steer --no-wait" does not describe steer's actual
control.

The failure shape is one of:

```json
{"error": {"code": "holder-timeout", "stage": "read", "timeout_s": 30.0, "message": "timed out"},
 "outcome": "unknown", "mutation_performed": null, "mutation_status": "unknown",
 "prompt_fingerprint": "sha256:...",
 "verify": {"command": "kaola-acp grok status --repo REPO --session SESSION",
            "match": "last_prompt.fingerprint",
            "note": "A read-stage timeout may still be admitted. ...",
            "do_not": "resend before checking status/capture"}}
```

and, for connect/send, the same error code with `"outcome": "not_sent"`,
`"mutation_performed": false`, `"mutation_status": "not_started"`. The request text is never
copied into a failure receipt. The `verify` surface is the real one: a prompt and an interrupt
use `status`/`last_prompt.fingerprint` (an interrupt's follow-up prompt is this steer's text); a
native steer uses `capture --since 0`, where the receipt's `steer_fingerprint` is on the
`steer_sent` event and that event's `request_id` joins the `steer_result` event's
`steer_outcome`/`steer_consumed`/`steer_confirmation`. A `steer_sent` or `written` event alone is
not adoption.

A read-stage timeout is genuinely uncertain. The request frame was written, and a holder that was
merely stopped or slow can admit it after the client gave up; `SIGCONT` evidence for this issue
showed the abandoned prompt completing with the exact `last_prompt.fingerprint`. Check `status`
and `capture` for the fingerprint before deciding, and never resend blindly. `status` can still
show the previous (or empty) turn while an admission is in progress: the holder publishes a turn
only after the agent frame is written (Issue #381), so `turn_active: false` during a blocked
admission is not proof that the request was not delivered.

A wedged holder remains recoverable. `stop --force` skips pending-permission settlement, which is
the one path that used to wait on the same admission lock a blocked prompt holds; it therefore
answers well under its 30 s bound for a lock-wedged holder and kills the agent group. A send blocked on
that admission then receives a definitive `acp-write-failed` with
`mutation_performed: false`/`mutation_status: not_started` (or the connection closes), so its
recovery is not another guess. The holder still writes an agent stdin while holding its admission
lock; this issue bounds the client and keeps force-stop available, but it does not shorten that
holder-side critical section.

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
covers them. A holder-lost `stop`, with or without `--force`, applies the same identity checks to `record.json` and
`children.jsonl` after a matching or omitted `--expected-holder-instance-id` (a foreign id is refused and writes one `holder_instance_mismatch` event), SIGKILLs the live members of the recorded agent group (only under a live leader
with the recorded `agent_started`, Issue #191) plus the confirmed child
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

### Invalid Runner input (Issue #260)

Both `kaola-tmux.sh` and `kaola-acp.py` return one JSON receipt on stdout and
exit nonzero for invalid arguments. The receipt has `schema_version: 3`,
`error.code: invalid-input`, `mutation_status: not_started`, and
`mutation_performed: false`. No holder is contacted by that invalid call.
These fields describe that call only. They do not change the result or state
of an earlier call. Do not repeat an earlier mutation without its receipt or
session evidence. `--help` still prints usage text and exits 0.

Runner `send` accepts `--text TEXT`, or prompt text from stdin when `--text`
is omitted. It does not accept `--text-file`. The direct Python entry accepts
`--stdin`. `start` reads a brief only when `--stdin` or `--text` is passed
(`--stdin` wins); that brief is the first turn above. A start with neither
flag does not read stdin. To send a file through the platform Runner, redirect stdin:

```bash
bash /absolute/path/to/scripts/kaola-tmux.sh codex send \
  --repo /absolute/project/root --session exact-session < /absolute/prompt.txt
```

If Python itself is unavailable, the shell reports that error on stderr; it
cannot create a JSON receipt. Parser errors omit supplied values because a
value can contain prompt text or a secret.

DSH next-step steering (#263): the local ACP adapter loads one in-process Cordis plugin
through the documented `dsh --profile acp --patch` overlay. The existing `_session/steering`
KPR-owned contract checks the owned ACP session and original prompt request before one private-socket
write. It is an adapter extension, not a vendor ACP method. The plugin calls supported `agent.steer`, the same operation used by the shipped session
controller. `native-admitted` confirms its next-step inbox admission, with consumption null.
The native operation can route to next-turn after an independent abort; the socket reply does
not claim an exact inbox target or processing. Processing needs session output. Native ACP still owns the original request and stream. An idle
local guard writes nothing; a native turn-end race can admit a detached later turn. That result
is reported as `started_new_turn`. No cancel or retry occurs. The adapter uses the exact DSH_BIN
and a process-local overlay; it changes no profile or global configuration. A custom direct ACP
command omits the adapter. Its local plugin and socket are removed when the adapter ends.

A missing measured Host Skill entry keeps the compact reload pending. Recover the
applicable installed Host Skill entry from the current authorized records; do not
clear the duty or guess an entry. A holder run from source does not name the checkout
directory as an installed platform Skill file. Its reminder names the platform
Skill and asks the worker to locate and read the full installed file through its
Skill catalog or active task records. Reminder admission does not prove that read.
