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
`named_tiers`, and `fast_support`/`fast_summary` (Issue #188). Only `default` is common;
`named_tiers` is the comma-separated list of the platform's own tier words (empty for none), and
each word `W` carries `<w>_model_name`/`<w>_model_id`/`<w>_model_parameters`/`<w>_model_effort`/`<w>_model_profile`
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
install`; only an unfiltered request reports `scope: complete`. Names this checkout no longer
generates but a receipt still owns are obsolete copies: the installer retires one only when no
other referrer remains and the copy's bytes still match the receipt, and preserves — with a
named owner-safe next action — a modified, co-owned, foreign, or unreceipted path.

Droid's executable override is `DROID_BIN`. Its ACP command is the native
`droid exec --output-format acp`; no bridge or translator is used. Droid defaults to Auto Model
(`model=auto`) and full bypass (`autonomy_level=auto-high`). The supported
`--permission-mode` values are `bypassPermissions|low|medium|high|manual`; ACP maps them to
`auto-high|auto-low|auto-medium|auto-high|normal` through `acp_mode_config_id: autonomy_level`.
ACP model, reasoning-effort, and autonomy options use config IDs `model`, `reasoning_effort`, and
`autonomy_level`. Droid's default preset is Auto (`auto`); `--tier opus` is Opus 5.5 (`claude-opus-5-5`,
`reasoning_effort=medium`) and `--tier core` is Kimi K3 (`kimi-k3`, `reasoning_effort=max`); it has no
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

Human watch is not an L0 receipt. `kaola-acp list [--platform P] [--repo ROOT]` and `kaola-acp survey` (below) are the only commands without a required platform positional or `--repo`; stdout is one `kaola-acp-list/1` object of live holders; `--include-dead` (Issue #132) adds records whose holder PID is gone. Each row also carries `identity` (`verified` | `dead` | `unreachable` | `mismatch`: record, live PID, answering admin socket, and a `state` reply whose `holder_instance_id` equals the record's, probed with a 5 s bound), `host_class` (the standard Host name `<platform>-<CODE>-orchestrator-<purpose>`), `dispatcher` (the dispatching holder identity the holder inherited from `KAOLA_ACP_DISPATCHER`, or `null`), and the binding fact `heartbeat_host` / `heartbeat_host_known`. `kaola-acp <platform> view --repo ROOT --session NAME [--since CURSOR]` stdout is one `kaola-acp-view/1` object. `kaola-acp <platform> follow --repo ROOT --session NAME [--since CURSOR] [--format text]` keeps the Unix socket open and writes NDJSON `{kind:snapshot|delta|heartbeat|eof|error}` lines; snapshot/delta payloads reuse `kaola-acp-view/1`. After the first `follow` op that FD is read-only (`prompt`/`permit`/`cancel`/`stop` reply `kind=error` and must use another short connection). A slow follower whose queue exceeds 256 lines gets `follow-dropped` and disconnects; other followers, `view`, and agent stdio continue. Killing the follow CLI does not stop holder/agent. Agent exit emits `kind=eof`, after which the holder closes that connection and the CLI exits; a dead holder emits `kind=error` `holder-lost`. View caps are enforced, not only flagged: thinking keeps an 8 KiB tail, one tool's content is clipped to 32 KiB, the timeline keeps the newest 200 messages, and a view over 256 KiB drops its oldest tools then oldest messages (`truncated=true`). Chunks without `messageId` join the previous same-role message until a tool call, new prompt, or turn end. `--format text` joins message/tool titles into tty text (not a TUI). Runtime facts use `error.code` in `holder-lost` / `holder-unreachable` / `no-session`. `kaola-tmux.sh PLATFORM view` prints `{"error":{"code":"view-unsupported","message":"view is not a Runner command; use kaola-acp"},"schema":"kaola-acp-view/1"}`, exit 1; `follow` is likewise `follow-unsupported` (`"kind":"error"`). `install-local.sh --bin-links` (default on for the Codex runtime destination) also installs owned `$HOME/.local/bin/kaola-acp`, `kaola-acp-holder`, and `kaola-project-runner-locate` symlinks.

Installed platforms are a separate host-wide fact (Issue #147). `kaola-acp survey [--platform P] [--login-shell SHELL]` is read-only: it starts no agent, opens no ACP session, creates no holder, record, or record root, runs no platform binary (not even `--version`), and so spends no model turn. Its only child process is one non-interactive login shell (`SHELL -l -c`, stdin closed, bounded to 10 s and killed as a group on timeout), started from a fresh minimal environment (`HOME`, `SHELL`, `PATH=/usr/bin:/bin:/usr/sbin:/sbin`, `TERM=dumb`, plus `USER`/`LOGNAME`/`TMPDIR`/`LANG` when set), that prints its environment; the shell is `--login-shell`, else the account's login shell, else `$SHELL`, else `/bin/zsh`. A client with a narrow PATH (a GUI app subprocess) therefore sees what a new login sees. A `.zshrc`-only PATH edit is interactive-only and is not part of the login environment. Stdout is one `kaola-acp-survey/1` object, exit 0: `{schema, login_env, platforms}`. `login_env` is `{shell, shell_source: argument|account|SHELL|default, status: ok|unavailable, detail, path}` (`path` is the login PATH, `detail` says why it is unavailable). `platforms` has one row per platform in Runner order (`claude-code`, `codex`, `cursor-cli`, `devin`, `droid`, `dsh`, `grok`, `kimi-cli`, `opencode`, `zcode`; `--platform` keeps one), every row with the same keys: `platform`, `runtime_name`, `status` (`present` | `absent` | `unknown`), `installed` (`status == present`), `path` (the resolved executable or `null`), `source`, `binary`, `binary_env`, `requires_env`, `process_path`, and `login_path` (the manifest `binary_name` resolved on the invoking PATH and on the login PATH, each an executable path or `null`). `source` follows the Runner's launch order: `binary_env` (the manifest override in the invoking environment), `process_path`, `login_binary_env` (the same override exported by the login shell), then `login_path`. `absent` means neither environment resolves it; `unknown` means the invoking environment does not and the login environment could not be read, so absence is not established. ZCode keeps its launch rule: `binary` and `binary_env` are `null`, `requires_env` is `["KAOLA_ZCODE_ENTRY", "KAOLA_ZCODE_NODE"]`, and the row is `present` (`source` `process_env` or `login_env`, `path` the entry) only when both are absolute paths to an existing entry file and an executable runtime in one environment; a `zcode` on PATH or an installed application bundle is not probed. OpenCode Go is a provider route inside the `opencode` and `dsh` CLIs, not a separate binary, so those two rows carry it. `install-local.sh --bin-links` exposes the survey as `$HOME/.local/bin/kaola-acp survey`.

Quota packages are a separate read-only catalog (Issue #148). `kaola-acp packages [--platform P] [--installed-only] [--login-shell SHELL]` and `kaola-acp model-package --platform P --model ID` start no agent, open no session, create no holder or record, and spend no quota. Login environment is not required. `--installed-only` reuses the survey and keeps platforms whose `status` is `present`; only that flag runs the login shell. Stdout is one JSON object with sorted keys, exit 0. `packages` is `kaola-acp-packages/1`: `{schema, installed_only, platforms}` plus `login_env` only when `--installed-only`. Each platform row is `{platform, packages:[{id, name, windows, binds_models}]}`. `id` is `<platform>:<token>`. `windows` remains null or an array of strings: current values are `5h`, `weekly`, and `monthly`; multiple known periods can be listed together. An empty array means the package is verified to have no time-based reset window; null means the package-level period is not established. This field names confirmed reset periods only, not quota amounts or reset timestamps; an unlisted period is not proven absent unless the provider documents the complete set. Factory's Individual Plans docs specify three rolling windows (5-hour, 7-day, and 30-day) for individual-plan Standard Usage. Droid Standard therefore lists `5h`, `weekly`, and `monthly`. Droid Core is a separate Rate Limit pool after Standard Usage is exhausted; the docs do not specify Core window periods, so the catalog keeps only the owner-confirmed weekly and monthly periods for Core and does not infer a 5h window ([Factory Individual Plans](https://docs.factory.ai/pricing/individuals)). Kimi exposes both `kimi-cli:managed` (weekly and monthly) and the additive `kimi-cli:managed_monthly` (monthly only); Kimi model identifiers expose the same `kimi-code` prefix for both plans, so the new variant does not bind models and consumers need account-plan context to select it. Droid `extra_usage` uses an empty window list because Factory describes its prepaid credits as non-expiring (same source). Current unresolved package periods remain null for `claude-code:extra_usage` (the supplied facts establish subscription periods, not this extra-usage balance), `devin:overage` (no period is established for this separate overage entry), and `opencode:zen` (no Zen-specific period is established; the OpenCode Go fact does not cover it). `model-package` is `kaola-acp-model-package/1`: `{schema, platform, model, packageId, status}` where `status` is `mapped` or `unmapped` and `packageId` is the qualified id or null. A usage error exits 2. An id with no verified rule is unmapped, never a guessed package. A static query (no live row) may still map an owner-confirmed preset id through the manifest's static preset map, and a live row's present native field value still wins over that static map. Example, mapped: `{"model": "grok-4.7", "packageId": "grok:account", "platform": "grok", "schema": "kaola-acp-model-package/1", "status": "mapped"}`. Example, unmapped: `{"model": "brand-new-model", "packageId": null, "platform": "droid", "schema": "kaola-acp-model-package/1", "status": "unmapped"}`. `observe`/`status` stamp model leaves on the emitted receipt only (`quotaPool` qualified id, or `quotaPool` null and `quotaPoolStatus` `unmapped`). `view` adds `models.availableModels` and `models.options` (the model config option only) from a copy. Stored `session_meta` and `record.json` stay the native ACP payload. The Project Runner reference is `references/quota-packages.md`.

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
`requested_model_name`, `requested_tier`, `requested_fast`, `resolved_runtime_model_id`,
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

Launch evidence (Issue #203). After applying the selection, `start` hands its own evidence to the
holder, which keeps it as `start_evidence` in `record.json` and every `status`/`observe` reply (from
the record when the holder is stopped or lost), across every whole-record rewrite. It is the start
receipt's `model_selection`, `config_application`, `effective_selection` (including
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
(`claude-opus-5-5` at `reasoning_effort=medium`) and `--tier core` is Kimi K3 (`kimi-k3` at
`reasoning_effort=max`). These ids are catalog values, so `acp_model_map` stays empty. `--tier alternative` stays the typed `tier-not-declared` refusal. Its native ACP mode option is
manifest-driven as `acp_mode_config_id: autonomy_level`; the default bypass value is
`auto-high`, and there is no bridge or translator.

Claude Code's `--tier default` is Opus (`opus`) at `effort=xhigh` (Elite; planning and
review, and it does not perform implementation). `--tier sonnet` is Sonnet (`sonnet`)
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
