# Issue #98 — repo-side integration design (mission 2)

Built on the measured facts in `dsh-acp-facts.md`. Every claim below was checked against the code,
not inferred from the OpenCode manifest's shape.

## What does *not* need to change

Three things I expected to need work and do not:

1. **Resume.** `kaola-acp-holder.py::initialize_agent` and `initialize_agent_resume` already branch
   `session/resume` vs `session/load` on `agentCapabilities.sessionCapabilities.resume`, and already
   tolerate a resume result with no `sessionId`. dsh advertises `resume`, so it takes the existing
   branch. **No holder edit.**
2. **`set_config_option`.** The holder already sends the parameter as `configId`, which is exactly
   what dsh's schema demands (`configOptionId` is rejected `-32602`).
3. **The ACP protocol version.** dsh negotiates `1`, the Runner's `PROTOCOL_VERSION`.

So this issue is a *registration* change plus one manifest and one adapter — not a transport change.
Anything larger would be the speculative generalisation the issue forbids.

## Registration surface — every hardcoded roster

Derived by inventorying the files that name `droid`, the last platform added (Issue #58), and
discarding generated output and archives.

| File | What must change |
|---|---|
| `platforms/dsh.yaml` | **new** manifest |
| `scripts/adapters/dsh.sh` | **new** adapter |
| `scripts/render-skills.py:840` | the exact-inventory tuple and its error string |
| `scripts/kaola-acp.py:34` | `PLATFORMS` tuple. **No** `ACP_SKIP_MODE` entry — there is no mode option |
| `scripts/kaola-tmux.sh:64` | the `case "$platform"` allowlist |
| `scripts/kaola-locate.py:63` | `WORKER_IDS` |
| `scripts/kaola-grok-bot-verify.py:46` | `WORKER_IDS` |
| `scripts/kaola-model-policy.py:130` | `probes_for` — a **plain dict lookup**, so a missing entry is a `KeyError`, not a graceful default. `dsh` gets `[["--version"]]` |
| `scripts/install-local.sh:59,91,200` | usage text, skill-name case, default selection |
| `templates/orchestrator/*` | worker-roster prose |
| `tests/contract/*` | roster/inventory suites (mission 4) |
| `README.md`, `AGENTS.md`, `CHANGELOG.md`, `docs/api.md`, `docs/architecture.md` | nine → ten |

`scripts/render-skills.py` itself globs `platforms/*.yaml`, so the Skill is generated automatically
once the manifest exists; only the inventory assertion is hardcoded. `templates/budgets.json` is
per-class, not per-platform, so a tenth worker needs no new budget — but the new worker Skill must
fit the existing `worker_skill_bytes: 12288`.

## Manifest values, each with its evidence

| Key | Value | Why |
|---|---|---|
| `id` / `skill_name` | `dsh` / `dsh-kaola-project-runner` | roster convention |
| `runtime_name` / `display_name` | `dsh` / `dsh Kaola Project Runner` | `agentInfo.name` is `deepseek-harness-acp`, but the user-facing binary is `dsh` |
| `binary_name` / `binary_env` | `dsh` / `DSH_BIN` | convention |
| `session_prefix` | `dsh-kaola` | convention |
| `default_transport` | `acp` | PTY out of scope |
| `acp_command` | `dsh --profile acp` | measured |
| `acp_client_capabilities` | `terminal:false,fs:false` | dsh rejects `terminal/*` and client fs; the Runner's existing defaults were accepted |
| `acp_verified_versions` | `cli=0.1.5-rc.2;agent=deepseek-harness-acp/0.0.1;protocol=1` | measured |
| `acp_login_requires_pty` | `false` | `authMethods: []`, `authenticate` → `{}` |
| `acp_env_allowlist` | `DSH_HOME,DEEPSEEK_API_KEY` | dsh's own error names `DEEPSEEK_API_KEY` as the launching-environment escape; `DSH_HOME` selects the profile root |
| `acp_mode_config_id` | `""` | no `mode` option; `session/set_mode` is `-32601` |
| `acp_model_config_id` | `model` | measured |
| `acp_effort_config_id` | `reasoning_effort` | measured (route-dependent) |
| `acp_fast_config_id` / `acp_fast_values` / `fast_support` | `""` / `""` / `none` | no Fast surface |
| `native_steering` / `acp_steer_method` | `unsupported` / `""` | four candidate methods all `-32601` |
| `continue_syntax` | `unsupported` | `session/list` has no `updatedAt`, so `latest_session()` is permanently ambiguous; and the acp profile takes no CLI args |
| `resume_syntax` | `session/resume <session-id> (ACP)` | there is no PTY flag; resume is a protocol call |
| `default_model_*` / `upgrade_model_*` | CLI-native, no override | the OpenCode precedent: the Runner does not pick dsh's model |
| `acp_wrapper_pin` / `acp_init_meta` | `""` | no vendored bridge, no `_meta` needed |

### `acp_model_map`

dsh's `model` option values are **JSON-encoded two-element arrays as strings**
(`["deepseek-official","deepseek-v4-pro"]`), which no caller would type. Without a map, `--model`
is unusable on dsh: the bare picker ID would be rejected and recorded as a limitation. The map
format (`;`-separated, `=`-partitioned) tolerates these values because they contain neither `;` nor
`=`. So `acp_model_map` gets the shipped catalog's routes keyed by plain ids. This is the escape
hatch the credential problem below needs; it adds no mechanism, only manifest data.

## The credential precondition — the one thing an operator must know

The shipped `@deepseek-ai/dsh-acp-app` patch pins `provider: deepseek-official, model:
deepseek-v4-flash` and **ignores** the user's `agent-default-model` setting. On a machine whose
credential is for another provider, `session/new` still succeeds and only the first
`session/prompt` fails `-32603 … no API key for provider route "deepseek-official"`.

A start receipt that says `ready` therefore does not prove the session can answer. Two operator
resolutions, neither touching `~/.dsh/`: export `DEEPSEEK_API_KEY`, or pass `--model` so the Runner
selects a credentialed route through the existing `set_config_option` path. This belongs in
`acp_quirks` and in the generated `references/acp.md`, stated as a start-time caveat rather than
buried.

## The permission statement

OpenCode's line is "no ACP skip-all; PTY `--auto` is the bypass". **Copying that shape for dsh would
be wrong in both halves.** dsh has no PTY bypass in scope, and more importantly it has no gate:
two live tool turns, including a bash write to an absolute path outside the session workspace,
produced zero `session/request_permission` calls and both writes landed. So dsh's honest default is
*already unattended*, and the manifest must say so rather than imply a restriction that does not
exist. `ACP_SKIP_MODE` correctly gets no `dsh` entry — not because a skip is unavailable, but
because there is nothing to skip.

## Adapter shape

`scripts/adapters/dsh.sh` follows `opencode.sh` minus everything PTY-specific that dsh cannot
honour. `adapter_build_launch` has no resume/continue flags to add (the acp profile accepts no
arguments; resume is a protocol call), `adapter_prepare_model_environment` is empty (model selection
travels over ACP, not env), and `adapter_detect_tui` / `adapter_activity_hint` stay conservative
because no dsh TUI is in scope this round.
