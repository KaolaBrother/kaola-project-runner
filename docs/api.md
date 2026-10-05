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
is sent literally and a rejection is reported as a limitation. `acp_command_default`
and `acp_command_<w>` (for a named tier) are optional per-tier spawn commands (Issue #140; only
Devin declares them, as `devin acp --model <preset id>`): when the tier preset selects the model,
`kaola-acp.py` spawns that command instead of `acp_command`, while `--command`,
`KAOLA_ACP_COMMAND`, an explicit `--model`, or a preserved resume keep the base; an empty value, or
`acp_command_<w>` for an undeclared tier, is rejected. `acp_session_new_timeout` is an optional
number of seconds in (0, 600] the holder waits for the `session/new` answer in `start` and the
`preflight` probe (Issue #146; absent keeps 15 s; only Codex declares it, `60`, because live Codex
answered after ~18 s). The client start window (20 s) and the probe bound (60 s) grow by the
amount it exceeds 15 s, keeping the margins they had over the default wait; the holder reports
no answer in time as `acp-session-timeout`. Model-selection fields are
`default_model_name`/`default_model_id`/`default_model_parameters`/`default_model_effort`/`default_model_profile`,
optional `default_model_components`, `named_tiers`, and `fast_support`/`fast_summary` (Issue #188, components Issue #237). Only `default` is common;
`named_tiers` is the comma-separated list of the platform's own tier words (empty for none), and
each word `W` carries `<w>_model_name`/`<w>_model_id`/`<w>_model_parameters`/`<w>_model_effort`/`<w>_model_profile`
and may carry `<w>_model_components`
with `w` = `W` with `-` as `_` (name and id required; a profile may be empty and has no `|`,
Issue #190). Profiles are selection guidance rendered only into Project Runner's
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
```

Platform IDs are `grok`, `claude-code`, `opencode`, `kimi-cli`, `cursor-cli`, `devin`, `codex`, `zcode`, `droid`, and `dsh`.
Omit `--platform` for all ten workers. `--platform` never selects the main Skill;
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
   unresolved `unknown` is a missing fact to resolve, not guessed absence. Installing ten
   Skill folders does not prove ten CLIs are present. Do not install an absent CLI
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
`0.1.7-rc.2` (ACP protocol 1). Its launcher pins both harness packages to the same exact version,
so there is no standalone harness upgrade. Keep a matching installation. If the selected DSH
install is elsewhere, set `DSH_BIN` to that binary. If either harness package is missing or too
old, the recovery is to install/update the whole `@deepseek-ai/dsh` package, for example
`npm install -g @deepseek-ai/dsh@0.1.7-rc.2` with the npm prefix that installed it; apply the
authorization rule above before that whole-CLI action. For changed or unverified DSH layers, the
existing bounded check is `preflight`, `start` (the receipt's `transport.agent_info` confirms the
ACP handshake, not the package version), `status`, and exact `stop`; it needs no model turn. Report
any model, provider, or credential failure separately without changing those settings.

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

## Dispatch and collect (`kaola-dispatch.py`)

The orchestrator Skill ships one entry, `scripts/kaola-dispatch.py`, for an
adopted research, QA, or report plan. `project` prints a compact capability
summary taken from the profile text of presets that are authorized and marked
present, plus the eligible candidates' exact preset ids, Class, catalog
profile, selection parameters, and structured restrictions. `execute` admits
that plan through each platform's existing `runtime-tmux.sh` and writes a
correlation index (`correlation_only`); a `--no-wait` admission is `in-flight`,
not a result. `collect` later correlates one status and, for a completed
turn, one capture, without waiting out a slower sibling. `snapshot` writes
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

Plan items may carry `task_id`, `output`, and `requires` (`{"class": ..., "presets": [...]}`, a
requirement the Host stated for that item). All three are copied onto the index row. An
unmet `requires` is `not-run` / `requirement-unmet` before any Runner call; an item without
one is not compared. The index records `dispatcher` (the caller's `KAOLA_ACP_DISPATCHER`)
apart from each row's `notify_target` (the start receipt's `heartbeat_host`).

### Lifecycle state (`kaola-dispatch.py state`, Issue #255)

`state` maintains `<project>/.kaola/heartbeat-prompt.json` at schema
`kaola-heartbeat-prompt/2`: a structured `state` (`project`, `authorization`, `sideagent`,
`recovery`, `unverified`, keyed `tasks`/`holds`/`alerts`/`decisions`, capped `retired`
tombstones), a file `revision`, an optional `carrier`, and a generated `body` that is the
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
  settled decision, or any hold or alert; a later update of that id is `record-retired`. A
  task's `dispatch` items must be closed in `--index`, and every seat it names (`assignments`,
  `sessions`, `session`, including migrated ones with no index match) must show its session
  `stopped` in `--live` under the holder the task recorded (`holder_instance_id` on an
  assignment, on a `sessions` object, or beside the task's own `session`); a missing row, a
  live or stopped row of a different holder, or two different recorded holders for one seat
  is not proof of stop, and `check --live` reports it as `done-seat-open`. `retire --handoff
  TASK` instead moves the dispatch refs, `sessions` and `assignments` (each object marked
  `handed_from`, keeping its holder and evidence; the task's own `session` becomes such a
  `sessions` object) to another current task, which then owns their stop; the tombstone
  records `handed_to`, `seats` and `dispatch`. A task in `review` without
  a verdict is under `attention` with a `content` digest, so each new result is a new wake; a
  task at `closeout` or `done` without an `accepted`, `partial` or `cancelled` verdict stays
  under `attention` as `verdict-missing`. Each write records `writer`; a `host` write from a
  caller whose own record names no role reads `host:<session> (role unverified)`, because the
  writer flag is a trace, not an identity proof. On migration a v1 `pending` key with no v1
  meaning is kept under the task's `legacy` and never acts as a v2 field of the same name.
- Each Host business write raises the file's `host_revision` and stamps the record (or
  section source, or tombstone) with it; tool and Sideagent writes do not raise it and stamp
  the caller's holder as `writer_holder`. Task `dispositions` maps item ids to `accepted`,
  `repair`, `cancelled`, `superseded` or `handed-off` (Host-owned); `update --kind tasks
  --index I` mirrors them onto the index `acceptance` with `acceptance_source`, and after a
  task `verdict` an item of that task with no disposition becomes `undecided` with an
  `acceptance_note`. The mirror result is `index_mirror`; a mirror error does not fail the
  state write.
- `checkpoint --writer sideagent --batch B --through-host-revision R --entries JSON
  [--events JSON]` (`--events` is accepted for older carriers) is written by a node-mode Sideagent (`sideagent.mode: "node"`) from inside
  its own session. Each entry names an `input` (a Host change id `host:<kind>/<id>@<rev>`,
  `host:section/<name>@<rev>`, `host:retired/<kind>/<id>@<rev>`, or a worker event id) and
  either `applied` (current records or `retired:<kind>/<id>` this node's holder wrote) or
  `retained` (a current record with `next`, `owner` or `wait`, or a Host `section/<name>`).
  The checkpoint lands in `maintenance.last_checkpoint`; `last_verified` moves only when every
  selected input settled; an entry for a batch change the Host rewrote after `R` is listed
  under `superseded`, not returned, since the rewrite is the next batch's input; `acked_host_revision` never passes an unsettled change or one still
  open in the `maintenance-returned` alert, which receives each unsettled input once. A
  caller that is not the session's current node holder is `binding-superseded`; no caller
  identity is `node-identity-required`.
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
  are not news to it); partial, missing, or a checkpoint `through` below the sent range reaches the Host
  once naming the unhandled range, and that range is not sent again. A batch the node does not
  admit, a failed start and a lost node are staged for the Host once as a `node` item naming
  the unhandled range; the first two start no further node until the binding changes. The
  carrier then exact-stops the node. A stop is confirmed when the node's holder process is
  gone, not by its `stopped` record; while it still runs (`sideagent_node_stop_unconfirmed`)
  no node starts, and once it is gone (`sideagent_node_stop_confirmed_late`) the next Host
  change starts a fresh node. A holder whose stop reply cannot be delivered still exits.
  A node is the carrier's own session, not a dispatched worker: a Host `stop` in every mode
  (default, `--force`, `--preserve-dispatched-workers`) starts no new node, waits up to 8 s
  for a node start in flight, and exact-stops the running node, found by its record's
  `dispatcher` when the start is still running.
- `view --role host|sideagent|delegator` reads only. The Host view adds `host_revision`,
  `dispositions` and a `maintenance` brief; the Sideagent view adds `host_revision` and
  `pending_host_changes`; the Delegator view adds `maintenance`. The Delegator view lists the `AGENTS.md`
  user-requirements region, holds, alerts, pending decisions, `unverified`, then doing, todo,
  and outcomes.
- `check [--index] [--live] [--repo]` reports problems without writing.
- `timer --repo --target --entry --body|--body-file` compares a native timer body with the
  entry line plus the fixed locator sentence; exit 1 on `mismatch`.
- `migrate` is a read-only plan unless `--write`; see
  [state-format migration](conventions.md#state-format-updates-and-migration).

The Host view is bounded at 64 KiB (`host-view-too-large`). The whole file is bounded at
1 MiB when `carrier.capability` is `heartbeat-state/2`, else at the 64 KiB legacy reader
limit (`carrier-limit`). The tool refuses rather than truncating a record.

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
  [--if-snapshot ID] [--text TEXT]
scripts/kaola-tmux.sh PLATFORM key       --repo ABS_PATH --session NAME \
  [--if-snapshot ID] --key NAME
scripts/kaola-tmux.sh PLATFORM answer    --repo ABS_PATH --session NAME \
  [--decision-id ID] [--if-snapshot ID] --replace-editor [--text TEXT]
scripts/kaola-tmux.sh PLATFORM stop      --repo ABS_PATH --session NAME \
  [--if-snapshot ID] [--force] [--preserve-dispatched-workers]
```

`--preserve-dispatched-workers` (also on `drain-restart`) is an explicit Host continuity
intent: the stop keeps the complete process tree (holder, native agent, tools) of each worker
this Host dispatched, proven by its spawn line or a live worker record naming this exact
holder as `dispatcher`, on a cooperative stop and on dead-holder cleanup; other recorded
children are still swept. A live holder that does not advertise `preserve-dispatched/1`
returns `{"result":"refused","reason":"preserve-unsupported"}` with `mutation_status:
not_started`. Without the flag a Host stop is unchanged. The successor Host then runs
`rebind-host` per seat; a start still in flight is not covered and needs reconciliation.

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

`--expected-holder-instance-id ID` binds `send`, `permit`, `cancel`, `key`, and `stop` to one ACP holder
instance. A mismatch returns `{"error":{"code":"holder-instance-mismatch"}}` with
`mutation_performed: false` and changes nothing, so a same-named session rebuilt by a later holder
is never stopped in place of the one the Agent verified.

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
or `standalone-default`), and a `detail` for blocking fallback. The legacy role fallback
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

Human watch is not an L0 receipt. `kaola-acp list [--platform P] [--repo ROOT]` and `kaola-acp survey` (below) are the only commands without a required platform positional or `--repo`; stdout is one `kaola-acp-list/1` object of live holders; `--include-dead` (Issue #132) adds records whose holder PID is gone. Each row also carries `identity` (`verified` | `dead` | `unreachable` | `mismatch`: record, live PID, answering admin socket, and a `state` reply whose `holder_instance_id` equals the record's, probed with a 5 s bound), `host_class` (the standard Host name `<platform>-<CODE>-orchestrator-<purpose>`), `dispatcher` (the dispatching holder identity the holder inherited from `KAOLA_ACP_DISPATCHER`, or `null`), and the binding fact `heartbeat_host` / `heartbeat_host_known`. `kaola-acp <platform> view --repo ROOT --session NAME [--since CURSOR]` stdout is one `kaola-acp-view/1` object. Its timing and permission-outcome fields (Issue #257) are holder-clock facts in Unix seconds with millisecond precision; ACP itself carries no timestamps. Each `messages[]` entry has `received_at` (float | null): the holder receipt time of the message's first chunk, equal to that chunk's `events.jsonl` `ts`, and `null` for the prompt message the holder itself wrote (that message has no event-log line). `turn` adds `started_at` (the time the holder wrote the `session/prompt` frame, the record's `last_prompt.written_at`) and `ended_at` (the `ts` of the `turn_ended` event, or of `process_exited` when the agent died mid-turn), each `null` while unknown. `turns[]` lists every prompt turn this holder process wrote, oldest first and capped at 200: `{started_at, ended_at, outcome, stop_reason, start_cursor, end_cursor}`, where `start_cursor` is the turn's prompt-message `cursor` and `end_cursor` the ending event's cursor, so a message whose `cursor` falls in `[start_cursor, end_cursor]` belongs to that turn. `answered_permissions[]` lists, in answer order and capped at 200, every permission answer the Runner wrote to the agent (`permit`, plus the `cancelled` answer `cancel`/`stop` writes for a pending request): `{request_id, title, tool_call_id, options, chosen_option, outcome, answered_at, cursor}`. `options` matches `pending_permissions[].options`; `chosen_option` is `{optionId, name, kind}` (only `optionId` set when the agent never offered that id) or `null` for `cancelled`; `outcome` is `approved` for an `allow_*` kind, `denied` for a `reject_*` kind, `cancelled`, or `unknown` for any other kind; `answered_at` is when the answer was written (for `permit`, the `permission_answered` event `ts`); `cursor` is the newest event cursor at that moment. A request the agent withdrew (`$/cancel_request`) or that vanished with the agent was not answered by the Runner and is not listed. These lists live in the holder's in-memory projection and start empty when a holder restarts; a dropped turn or answer sets `truncated`. Terminal and command output bodies are not added: they already arrive as tool `content`. `kaola-acp <platform> follow --repo ROOT --session NAME [--since CURSOR] [--format text]` keeps the Unix socket open and writes NDJSON `{kind:snapshot|delta|heartbeat|eof|error}` lines; snapshot/delta payloads reuse `kaola-acp-view/1`. After the first `follow` op that FD is read-only (`prompt`/`permit`/`cancel`/`stop` reply `kind=error` and must use another short connection). A slow follower whose queue exceeds 256 lines gets `follow-dropped` and disconnects; other followers, `view`, and agent stdio continue. Killing the follow CLI does not stop holder/agent. Agent exit emits `kind=eof`, after which the holder closes that connection and the CLI exits; a dead holder emits `kind=error` `holder-lost`. View caps are enforced, not only flagged: thinking keeps an 8 KiB tail, one tool's content is clipped to 32 KiB, the timeline keeps the newest 200 messages, and a view over 256 KiB drops its oldest tools, then oldest messages, answered permissions, and turns (`truncated=true`). Chunks without `messageId` join the previous same-role message until a tool call, new prompt, or turn end. `--format text` joins message/tool titles into tty text (not a TUI). Runtime facts use `error.code` in `holder-lost` / `holder-unreachable` / `no-session`. `kaola-tmux.sh PLATFORM view` prints `{"error":{"code":"view-unsupported","message":"view is not a Runner command; use kaola-acp"},"schema":"kaola-acp-view/1"}`, exit 1; `follow` is likewise `follow-unsupported` (`"kind":"error"`). `install-local.sh --bin-links` (default on for the Codex runtime destination) also installs owned `$HOME/.local/bin/kaola-acp`, `kaola-acp-holder`, and `kaola-project-runner-locate` symlinks.

### Session role

`session_role` (Issue #245) is one additive session identity on the holder record and on `list`, `status`/`observe`, and `view`/`follow`. Known values are `host`, `sideagent`, `expert`, `elite`, and `worker`. JSON `null` means the identity is not established. A legacy record that lacks the key is the same as `null`; nothing rewrites or restarts that seat to fill it. `host_class` stays the boolean name-pattern fact (`<platform>-<CODE>-orchestrator-<purpose>`, with the existing `-i<digits>-` worker exclusion) and is not replaced by this field.

Derivation, in order: a standard Host name is `host` (authoritative; `session_role` mirrors `host_class`). An explicit start `--role sideagent` — the current role flag — is `sideagent`. `expert`, `elite`, and `worker` come only from the preset this start actually selected (`selection_basis.preset_id`) and that tier's manifest `{tier}_model_class`, lowercased. A custom `--model`, a resume that preserves the native session without the same-native-session inheritance identity, an unknown class, or missing evidence is `null`. Session-name spelling, model-id substrings, session purpose, and an unrelated default preset are not evidence. Unknown is never labeled `worker`.

`list` projects `session_role` as `host` when `host_class` is true, otherwise the persisted record value, otherwise `null`. That is the consumer fallback for a legacy Host row: `host_class` true still reads as Host even when the stored field is missing. `status` and `observe` lift the persisted value to the top level next to `start_evidence` (a live state reply already carries it; a missing or unknown stored value is `null`). `view` and `follow` (snapshot, delta, and heartbeat) pass the holder value through. Only the one maintenance Sideagent bound in lifecycle state (`state.sideagent`, `state: active`) is outside `elite_cap` and preset counts; its row and index item carry `seat_exempt: true`, and a shared seat it occupies stays occupied. Every other `sideagent`-role item is counted as a worker under its preset Class (`evidence.seat_note`). A dispatch plan `role` of `sideagent` is passed as start `--role sideagent` and kept on the index for correlation. Apart from the legacy alias below, other `role` values stay index metadata: it does not authorize that role, relabel a holder, or refuse the item. The seat's `session_role` still comes from the Host name, that explicit sideagent flag, or the selected preset Class. Recovery does not re-send or change a live session's role; a persisted-versus-requested sideagent mismatch is a note only.

Legacy `sidekick` remains accepted in start flags and dispatch plans and stays
verbatim in existing holder records, receipts and indexes. Consumers render both
`sideagent` and `sidekick` as Sideagent. Recovery treats them as the same role
without relabeling a live session, replaying work or renaming any session. No
schema version changes. New callers use `sideagent`; unknown values still stay
unknown.

A native model component `role` (`main` or `sidekick` inside `model_display.components`) is a Fusion composition fact, not `session_role`.

Installed platforms are a separate host-wide fact (Issue #147). `kaola-acp survey [--platform P] [--login-shell SHELL]` is read-only: it starts no agent, opens no ACP session, creates no holder, record, or record root, runs no platform binary (not even `--version`), and so spends no model turn. Its only child process is one non-interactive login shell (`SHELL -l -c`, stdin closed, bounded to 10 s and killed as a group on timeout), started from a fresh minimal environment (`HOME`, `SHELL`, `PATH=/usr/bin:/bin:/usr/sbin:/sbin`, `TERM=dumb`, plus `USER`/`LOGNAME`/`TMPDIR`/`LANG` when set), that prints its environment; the shell is `--login-shell`, else the account's login shell, else `$SHELL`, else `/bin/zsh`. A client with a narrow PATH (a GUI app subprocess) therefore sees what a new login sees. A `.zshrc`-only PATH edit is interactive-only and is not part of the login environment. Stdout is one `kaola-acp-survey/1` object, exit 0: `{schema, login_env, platforms}`. `login_env` is `{shell, shell_source: argument|account|SHELL|default, status: ok|unavailable, detail, path}` (`path` is the login PATH, `detail` says why it is unavailable). `platforms` has one row per platform in Runner order (`claude-code`, `codex`, `cursor-cli`, `devin`, `droid`, `dsh`, `grok`, `kimi-cli`, `opencode`, `zcode`; `--platform` keeps one), every row with the same keys: `platform`, `runtime_name`, `status` (`present` | `absent` | `unknown`), `installed` (`status == present`), `path` (the resolved executable or `null`), `source`, `binary`, `binary_env`, `requires_env`, `process_path`, and `login_path` (the manifest `binary_name` resolved on the invoking PATH and on the login PATH, each an executable path or `null`). `source` follows the Runner's launch order: `binary_env` (the manifest override in the invoking environment), `process_path`, `login_binary_env` (the same override exported by the login shell), then `login_path`. `absent` means neither environment resolves it; `unknown` means the invoking environment does not and the login environment could not be read, so absence is not established. ZCode keeps its launch rule: `binary` and `binary_env` are `null`, `requires_env` is `["KAOLA_ZCODE_ENTRY", "KAOLA_ZCODE_NODE"]`, and the row is `present` (`source` `process_env` or `login_env`, `path` the entry) only when both are absolute paths to an existing entry file and an executable runtime in one environment; a `zcode` on PATH or an installed application bundle is not probed. OpenCode Go is a provider route inside the `opencode` and `dsh` CLIs, not a separate binary, so those two rows carry it. `install-local.sh --bin-links` exposes the survey as `$HOME/.local/bin/kaola-acp survey`.

Quota packages are a separate read-only catalog (Issue #148). `kaola-acp packages [--platform P] [--installed-only] [--login-shell SHELL]` and `kaola-acp model-package --platform P --model ID` start no agent, open no session, create no holder or record, and spend no quota. Login environment is not required. `--installed-only` reuses the survey and keeps platforms whose `status` is `present`; only that flag runs the login shell. Stdout is one JSON object with sorted keys, exit 0. `packages` is `kaola-acp-packages/1`: `{schema, installed_only, platforms}` plus `login_env` only when `--installed-only`. Each platform row is `{platform, packages:[{id, name, windows, binds_models}]}`. `id` is `<platform>:<token>`. `windows` remains null or an array of strings: current values are `5h`, `weekly`, and `monthly`; multiple known periods can be listed together. An empty array means the package is verified to have no time-based reset window; null means the package-level period is not established. This field names confirmed reset periods only, not quota amounts or reset timestamps; an unlisted period is not proven absent unless the provider documents the complete set. Factory's Individual Plans docs specify three rolling windows (5-hour, 7-day, and 30-day) for individual-plan Standard Usage. Droid Standard therefore lists `5h`, `weekly`, and `monthly`. Droid Core is a separate Rate Limit pool after Standard Usage is exhausted; the docs do not specify Core window periods, so the catalog keeps only the owner-confirmed weekly and monthly periods for Core and does not infer a 5h window ([Factory Individual Plans](https://docs.factory.ai/pricing/individuals)). Kimi exposes both `kimi-cli:managed` (weekly and monthly) and the additive `kimi-cli:managed_monthly` (monthly only); Kimi model identifiers expose the same `kimi-code` prefix for both plans, so the new variant does not bind models and consumers need account-plan context to select it. Droid `extra_usage` uses an empty window list because Factory describes its prepaid credits as non-expiring (same source). Current unresolved package periods remain null for `claude-code:extra_usage` (the supplied facts establish subscription periods, not this extra-usage balance), `devin:overage` (no period is established for this separate overage entry), and `opencode:zen` (no Zen-specific period is established; the OpenCode Go fact does not cover it). `model-package` is `kaola-acp-model-package/1`: `{schema, platform, model, packageId, status}` where `status` is `mapped` or `unmapped` and `packageId` is the qualified id or null. A usage error exits 2. An id with no verified rule is unmapped, never a guessed package. A static query (no live row) may still map an owner-confirmed preset id through the manifest's static preset map, and a live row's present native field value still wins over that static map. Example, mapped: `{"model": "grok-4.7", "packageId": "grok:account", "platform": "grok", "schema": "kaola-acp-model-package/1", "status": "mapped"}`. Example, unmapped: `{"model": "brand-new-model", "packageId": null, "platform": "droid", "schema": "kaola-acp-model-package/1", "status": "unmapped"}`. `observe`/`status` stamp model leaves on the emitted receipt only (`quotaPool` qualified id, or `quotaPool` null and `quotaPoolStatus` `unmapped`). `view` adds `models.availableModels` and `models.options` (the model config option only) from a copy. Stored `session_meta` and `record.json` stay the native ACP payload. The installed Project Runner reference `references/quota-packages.md` keeps the seat-failure rule only. For display, show the weekly or monthly window when the plan has one; show the 5h window only when it has neither.

One platform:

```json
{"installed_only": false, "platforms": [{"packages": [{"binds_models": true, "id": "grok:account", "name": "Account", "windows": ["weekly"]}], "platform": "grok"}], "schema": "kaola-acp-packages/1"}
```

A platform with several packages:

```json
{"installed_only": false, "platforms": [{"packages": [{"binds_models": true, "id": "droid:standard", "name": "Standard", "windows": ["5h", "weekly", "monthly"]}, {"binds_models": true, "id": "droid:core", "name": "Core", "windows": ["weekly", "monthly"]}, {"binds_models": true, "id": "droid:extra_usage", "name": "Extra usage", "windows": []}], "platform": "droid"}], "schema": "kaola-acp-packages/1"}
```

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

`rebind-host` (Issue #255) is the one in-place carrier change. Run from inside a live Host
session against an existing seat, it derives the target from that Host's own
`KAOLA_ACP_DISPATCHER`, checks the record is a Host-role, live, same-instance holder with its
socket, and sends the holder op `rebind_heartbeat_host`. The receipt carries `rebound`,
`previous_heartbeat_host`, `heartbeat_host`, and the unchanged `holder_instance_id`; the seat
logs `heartbeat_host_rebound`. Refusals are `{"result":"refused","reason":"rebind-host-unresolved"}`
exit 1 before the seat is touched, and holder errors `no-heartbeat-host` (seat started unbound),
`heartbeat-host-foreign-repo`, or `holder-instance-mismatch`. A holder that predates the op
answers `unknown-op`; that seat recovers through `drain-restart` as before. A Sideagent whose
own record names no Host now dispatches through the ordinary dispatcher rows. `rebind-host`
moves only the target seat's carrier: the seat's `dispatcher` still names the old Host, every
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
are swept exactly as for any dead holder (`force_killed_pids`: the agent's own process group only
while its live leader has exactly the start second the holder recorded as `agent_started` (epoch
seconds, so time zones do not matter) at spawn; plus
child groups that still match their recorded start time), and the record is retired once nothing of them is left
(later `status` reads `no-session`; a survivor keeps the record and appears in `residual_pids`). An
unreadable argv refuses `holder-unreachable`. A force stop of a dead
holder that leaves nothing of its recorded groups marks the record `stopped`, so `status` reads
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

- `--steer-mode native` uses the platform's own mid-turn entry and exists only where that entry
  really does. The manifest is the single source of truth: `native_steering` is `supported`,
  `unsupported` or `unknown` (an uninvestigated surface stays `unknown` and never masquerades as
  `unsupported`), `acp_steer_method` carries the entry and may be non-empty only when
  `native_steering` is `supported`, and `steering_summary` records the versioned evidence. Read the
  current roster out of `platforms/*.yaml` rather than from this page: which platforms qualify
  changes as surfaces are investigated, so no count or list is pinned here. One case worth knowing is
  `opencode`, whose `-32601` probe ran on 1.18.17 and whose 2.0.11 `initialize` advertised no
  steering `_meta`, while `acp_verified_versions` names 2.0.22 (permission QA only;
  2.0.15 was record-only since the 2026-09-24 Pink batch). No steering method was
  re-probed on any newer build: it is `unknown`, and the
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
"unsupported"`, never silently claimed. `--resume`/`--continue` without tier/model/effort preserves the
saved native session selection (`resume-preserved`); supplying any of them re-applies that selection.
There is no automatic escalation based on complexity, failures, or elapsed time. Catalog output is
reported as evidence and never rewrites or blocks the declared exact model literal. Actual mismatch,
catalog absence, or unreadable evidence never disables generic communication.

Model evidence under `model` on the `start`/`preflight` receipt includes `requested_model_source`,
`requested_model_name`, `requested_tier`, `requested_fast`, `requested_effort`, `model_display`,
`resolved_runtime_model_id`,
`resolved_parameters`, `resolved_fast`, and structured provenance. `actual_runtime_model_id` and
`actual_parameters` are `null` and `model_verified` is `unknown`
(`model_mismatch_reason: actual-model-evidence-not-yet-read`) on most platforms, because ACP
computes no true/false verdict from the launch request alone. Droid is the exception (Issue #185):
its selection is verified from the agent's own live current-model echo. Droid's only read-only
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
is that id with `effective_model_source: "launch-argv"`, the agent's own (possibly stale) value kept
as `advertised_model`. On such a launch-argv start Droid's `model_verified` compares that echoed
`advertised_model`, never the argv value the Runner itself supplied, so a session whose argv model
the agent never adopted verifies `false` instead of comparing the argv value to itself.
`status`/`observe` report the
agent's own current `session_meta.configOptions[].currentValue`. ACP `start` receipts additionally carry
`model_selection` and per-option `config_application` receipts; a rejected or unadvertised
`set_config_option` is reported as a limitation and leaves the session usable.

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
`Auto Model`, `DeepSeek V4.1 Flash`, `Kimi K3`, `Kimi K2.8`, `GLM 5.3`. `Flash` is the model
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
`actual_parameters`, and `model_evidence_provenance` without its `catalog_probe`, each present only
when the start receipt had it, plus `acp_session_id`, `resumed`, and `recorded_at`. It is evidence
from that start or resume, not a fresh observation: the current selection is
`session_meta.configOptions`, an applied option or launch argument is application evidence, and
only an existing verified fact (`model_verified: true`) is verified. `start_selection` stays the
caller's raw flags, so an omitted `--tier` is `null`. A resume or `--continue` whose adopted
`acp_session_id` equals the one the previous record for the same platform/session/repo ran and
recorded its evidence under keeps that evidence as `start_evidence.inherited` (`source:
"prior-holder-record"`, `holder_instance_id`, `acp_session_id`, `recorded_at`), also echoed as the
start receipt's `inherited_start_evidence`; a preserved resume carries the older applied evidence
forward flat. Any other native session, a Runner name alone, or a record without evidence inherits
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
at `effort=high` (Elite; an explicit preset and count grant, not a Worker-pool member).
Codex's `--tier luna` is GPT-6 Luna (`gpt-6-luna`) at `effort=max` (Issue #188): a
lower-cost worker choice, not an upgrade. These are applied as ordinary ACP config
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
`children.jsonl`, SIGKILLs the live members of the recorded agent group (only under a live leader
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
`--stdin`. To send a file through the platform Runner, redirect stdin:

```bash
bash /absolute/path/to/scripts/kaola-tmux.sh codex send \
  --repo /absolute/project/root --session exact-session < /absolute/prompt.txt
```

If Python itself is unavailable, the shell reports that error on stderr; it
cannot create a JSON receipt. Parser errors omit supplied values because a
value can contain prompt text or a secret.
