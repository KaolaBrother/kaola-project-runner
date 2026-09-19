# Issue #98 — dsh ACP capability facts (mission 1)

Measured live on this Mac, 2026-09-19, by driving `dsh --profile acp` directly over ACP JSON-RPC
stdio with `evidence/probes/dsh_acp_probe.py`. No proxy, no intermediate layer: the probe is the
ACP *client*, dsh is the agent.

## Versions and identity

| Fact | Value |
|---|---|
| Launcher | `/opt/homebrew/bin/dsh` → `/opt/homebrew/lib/node_modules/@deepseek-ai/dsh/lib/bin.js` |
| `dsh --version` | `0.1.5-rc.2` |
| ACP command | `dsh --profile acp` |
| `agentInfo` | `{"name": "deepseek-harness-acp", "version": "0.0.1"}` |
| `protocolVersion` | `1` (matches the Runner's `PROTOCOL_VERSION = 1`) |
| Bundles | `@deepseek-ai/dsh-acp-app` over `@deepseek-ai/dsh-base`, inserting `@deepseek-ai/dsh-acp` |

`dsh --profile acp --help` prints help and exits **without** claiming stdin/stdout, so a help probe
is safe. Stdout carried only newline-delimited JSON-RPC in every run; stderr was empty; every
probe process exited `0` after stdin EOF.

## `initialize` result, verbatim

```json
{"protocolVersion": 1,
 "agentInfo": {"name": "deepseek-harness-acp", "version": "0.0.1"},
 "agentCapabilities": {
   "mcpCapabilities": {"http": true},
   "promptCapabilities": {"image": false, "audio": false, "embeddedContext": false},
   "sessionCapabilities": {"close": {}, "list": {}, "resume": {}}},
 "authMethods": []}
```

Client capabilities sent were the Runner's own defaults —
`{"fs": {"readTextFile": false, "writeTextFile": false}, "terminal": false}` — and dsh accepted
them, consistent with its documented refusal of client filesystem operations and terminals.

## Method surface, measured

| Method | Result |
|---|---|
| `authenticate` | `{}` — immediate success, `authMethods` is empty; no login, no PTY login |
| `session/new` | `{sessionId, configOptions}`; `cwd` absolute, `mcpServers: []` accepted |
| `session/list` | `{"sessions": [{"sessionId", "cwd"}, …]}`, newest-first, `cwd` filter honoured |
| `session/resume` | OK; returns `configOptions` and **no `sessionId`** |
| `session/close` | `{}` |
| `session/set_config_option` | OK; parameter name is **`configId`** |
| `session/prompt` | `{"stopReason": "end_turn"}` |
| `session/cancel` (notification) | turn ends `{"stopReason": "cancelled"}` |
| `session/load` | **`-32601` Method not found** |
| `session/set_mode` | `-32601` |
| `session/delete`, `session/fork` | `-32601` |
| `terminal/create`, `terminal/output` | `-32601` |
| `_session/steering`, `session/steering`, `session/steer`, `_session/steer` | all `-32601` |

All ten `-32601` results above are preserved frame by frame in
`evidence/raw/method-surface.txt` (probe phase `methods`). The first version of this file
tabulated several of them from a probe whose output was not kept; the review caught that, and the
phase was added so the claim and the artifact match.

## Consequences for the Runner — each one already checked against the code

### 1. Resume needs no Runner change

`agentCapabilities.sessionCapabilities.resume` is present, and
`kaola-acp-holder.py::initialize_agent` already branches
`method = "session/resume" if capability_supported(session_caps, "resume") else "session/load"`.
dsh therefore takes the `session/resume` path that already exists. `session/resume` omits
`sessionId` from its result, and the holder already falls back to the requested id
(`self.session_meta.get("sessionId", resume)`). **No holder edit is required for resume.**

Live: session `e1995cb7-…` was prompted, closed, and then resumed in a *new* process; the resumed
session reported the model selection made before the close, so selection survives the restart.

### 2. `--continue` cannot work for dsh, and must not be claimed

`session/list` entries carry only `sessionId` and `cwd` — **no `updatedAt`**.
`kaola-acp-holder.py::latest_session` returns `(None, candidates)` as soon as any candidate's
`updatedAt` is missing, so the `--continue` path answers `continue-ambiguous` even when exactly one
session exists. This is honest refusal, not a defect to patch in this issue; the manifest must
record continue as unsupported rather than advertise a flag.

### 3. `session/set_config_option` already matches

The holder sends `configId`, which is exactly what dsh expects. `session/new` advertises two
options:

- `model` — a `select` whose values are **JSON-encoded two-element arrays as strings**, e.g.
  `"[\"opencode-go\",\"deepseek-v4.1-flash\"]"`. Groups: `deepseek-official`, `opencode-go`.
- `reasoning_effort` — `off` / `low` / `high` / `max`, default `high`. It is route-dependent: after
  switching to the `opencode-go` route, the returned complete option state contained `model` only.

There is **no `mode` config option** (`session/set_mode` is `-32601`), so there is no ACP mode
surface and nothing for a skip-all to select.

### 4. The shipped ACP route is unauthenticated on this machine — this is the real start gate

`@deepseek-ai/dsh-acp-app`'s patch hardcodes `provider: deepseek-official, model:
deepseek-v4-flash`, and it **ignores** the user's `agent-default-model` setting. A first prompt on a
default session fails:

```
-32603 Internal error: turn failed: llm-deepseek: no API key for provider route
"deepseek-official"; store DEEPSEEK_API_KEY through the credentials service (the web Models page
writes it), or export DEEPSEEK_API_KEY in the launching environment
```

Note the shape: `session/new` **succeeds**, and the failure only appears at the first
`session/prompt`. A start that looks healthy can still be unable to answer.

Two resolutions exist and neither modifies `~/.dsh/`:

- export `DEEPSEEK_API_KEY` in the launching environment (⇒ `acp_env_allowlist: DEEPSEEK_API_KEY`);
- or call `session/set_config_option` `configId: model` onto a route that does have a credential.

The second was proven live here: selecting `["opencode-go","deepseek-v4.1-flash"]` (the route this
machine's `~/.dsh/settings.yaml` already configures) made the same session answer in 2.52 s with
exactly `PROBE-98-OK`, `stopReason: end_turn`.

### 5. dsh ACP is unattended by default — there is no client permission gate

This is the finding that most affects how the platform must be described. Across two live
tool-using turns the client received **zero** `session/request_permission` requests
(`inbound_request_methods: []`), and the tool ran anyway:

- inside the workspace: `echo PROBE-98-TOOL > probe98.txt` → file written, `tool_call` /
  `tool_call_update status: completed`, turn `end_turn`;
- **outside** the workspace: `echo PROBE-98-OUTSIDE > /tmp/dsh98-outside-96254` → file written at
  that absolute path, again with no permission request.

So for dsh the honest permission statement is not "no skip-all available" but "**no approval gate
to skip**": the shipped `acp` profile executes tool calls, including writes outside the session
workspace, without consulting the ACP client. `session/request_permission` exists in the protocol
contract and the holder answers it, but this composition never sends one. That must be stated as a
security-relevant default, not softened into an OpenCode-style "no skip-all" line.

### 6. Steering: native unsupported, composite available

All four candidate steering methods answer `-32601` and `initialize` advertises no steering `_meta`
— the same outcome Issue #65 recorded for cursor-cli, devin, droid, grok, kimi-cli and opencode.
`session/cancel` is accepted as a notification and the turn settles **immediately**: measured
`cancel_settle_s 0.01`, `stopReason: cancelled` (contrast zcode's 70–100 s). So the existing
composite `--steer-mode interrupt` is the usable path and needs no raised `--cancel-timeout`.

### 7. Update stream

Observed `sessionUpdate` kinds: `agent_message_chunk`, `tool_call`, `tool_call_update`,
`usage_update`. No `plan`, `mode`, or presentation updates — consistent with the automation-only
contract.

## `~/.dsh/` integrity

No file under `~/.dsh/` was edited by this run. All 16 dsh configuration files
(`.anonymous-user-id`, `.credentials.yaml`, `.env`, `settings.yaml`, and every profile's
`cordis.yml` / `cordis.patch.yml` / `pnpm-workspace.yaml` / `package.json`) hash identically before
and after the probes: `DSH_CONFIG_UNCHANGED`, 16/16. dsh's own runtime additions under
`~/.dsh/sessions/` and `~/.dsh/storages/` are dsh writing its own session state while being used
normally, not an edit by this run. All probe sessions used a throwaway `cwd` under `/tmp`, so no
dsh session record was created against this repository.

## PTY: absent, and now measured rather than assumed

An earlier version of this file left PTY entirely under "not established" while the manifest and
README still asserted that no terminal UI exists — a claim with no artifact behind it. The registry
settles it without starting anything or writing to `~/.dsh/`:
`@deepseek-ai/dsh-app-boot`'s `PROFILE_TEMPLATES` ships exactly **`acp`, `headless`, `sdk`,
`sdk-minimal`, `web`** (`evidence/raw/profile-templates.txt`). There is **no `tui` template** — the
`--profile tui` in `dsh --help`'s examples names a *custom* profile a user would create. Of the
five, `web` is a browser app, `headless` answers one task and exits, `sdk`/`sdk-minimal` are
programmatic, and `acp` is this JSON-RPC server. None is a terminal-pane conversation UI, which is
why `--transport pty` is a diagnostic entry for dsh rather than a fallback channel.

What remains genuinely out of scope is *building* a PTY transport — for instance driving the
`headless` one-shot or the `web` app — which this issue was instructed not to do.

## Deliberately not established

- Whether an `acp` profile exists on a machine that has never created one. This machine already had
  `~/.dsh/profiles/acp`; creating one requires `--from-default-profile`, which **writes** to
  `~/.dsh/` and is therefore an operator precondition, not an action of this run.
- Image prompts (`promptCapabilities.image: false` here; the shipped docs make it route- and
  attachment-store-dependent).
