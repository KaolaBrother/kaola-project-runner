# Droid 0.220.0 native ACP surface probe

LIVE probe of Factory Droid CLI (`/Users/ylpromax5/.local/bin/droid`, v0.220.0, authenticated device pairing) over native ACP (`droid exec --output-format acp`). Driver spoke the exact Runner dialect from `scripts/kaola-acp-holder.py` / `scripts/kaola-acp.py` (initialize → session/new → session/set_config_option → session/prompt → session/resume|load|list|cancel; `session/request_permission` answered with `{"result":{"outcome":{"outcome":"cancelled"}}}`). Full transcripts: `/tmp/kaola-droid-acp-probe/probe-<tag>.log` (tags p1, p2, p2b, p3, p4, p5-flag, p5ctrl, p6). Scratch cwd `/tmp/kaola-droid-acp-probe/repo` (git, one README commit). All probes ran in fresh processes; each spawned pid was killed by exact pid and verified gone (see P-end residue check).

## P1 — initialize → session/new

`initialize` `{"protocolVersion":1,"clientCapabilities":{"fs":{"readTextFile":false,"writeTextFile":false},"terminal":false}}` returns:

```json
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":1,
 "agentCapabilities":{"loadSession":true,"sessionCapabilities":{"list":{},"resume":{}},
   "promptCapabilities":{"image":true,"embeddedContext":true},
   "_meta":{"terminal_output":true,"terminal-auth":true}},
 "agentInfo":{"name":"@factory/cli","title":"Factory Droid","version":"0.220.0"},
 "authMethods":[{"id":"device-pairing","name":"Login",...},{"id":"factory-api-key","name":"Factory API Key",...}]}}
```

Confirmed: **no `configOptions` key in the initialize result.**

`session/new` `{"cwd":"/tmp/kaola-droid-acp-probe/repo","mcpServers":[]}` returns result keys `sessionId`, `models`, `modes`, `configOptions` (sessionId `858c4700-cb88-4c1a-a45c-a46c6af3e467`):

- `models.availableModels`: 49 catalog ids, e.g. `auto` (Auto Model), `gpt-5.6-sol`, `gpt-5.6-sol-fast`, `gpt-5.5`, `grok-4.6`, `claude-opus-5`, `gemini-3.1-pro-preview`, `deepseek-v4-pro`, `kimi-k3`, `qwen3.8-max` … (full catalog in `p1-sessionnew.json`).
- `modes`: `availableModes` = normal (Auto (Off)), spec, auto-low, auto-medium, auto-high (Auto (High)); `currentModeId: "auto-high"`.
- `configOptions` (the config declarations that initialize omits — 3 options):

```json
[{"id":"autonomy_level","name":"Autonomy Level","category":"mode","type":"select","currentValue":"auto-high",
  "options":[{"value":"normal"},{"value":"spec"},{"value":"auto-low"},{"value":"auto-medium"},{"value":"auto-high"}]},
 {"id":"model","name":"Model","category":"model","type":"select","currentValue":"gpt-5.6-sol",
  "options":[{"value":"auto",...},...49 catalog values...]},
 {"id":"reasoning_effort","name":"Reasoning Effort","category":"thought_level","type":"select","currentValue":"high",
  "options":[{"value":"none"},{"value":"low"},{"value":"medium"},{"value":"high"},{"value":"xhigh"},{"value":"max"}]}]
```

- P1 session/update notifications: only `available_commands_update` (the droid skill commands). No `currentSessionConfigOption` field appeared anywhere; config state lives in the session/new result and in `config_option_update` notifications.

**Effective model evidence (P1, plain process): `model=gpt-5.6-sol`, `reasoning_effort=high`, `autonomy_level=auto-high`.**

## P2 — session/set_config_option candidates

One session; `session/set_config_option` params `{"sessionId":<sid>,"configId":<id>,"value":<v>}`. Accepted responses are `{"jsonrpc":"2.0","id":N,"result":{}}` followed by a `config_option_update` echo; rejected responses carry the error below and emit no update.

| configId | value | result |
|---|---|---|
| `model` | `auto` | **accepted** `result {}` → echo `model: "auto"` (also reset `reasoning_effort` to `none`) |
| `model` | `gpt-5.6-sol` | **accepted** `result {}` → echo `model: "gpt-5.6-sol"` |
| `reasoningEffort` | `high` | error `{"code":-32602,"message":"Invalid params: Unknown config option: reasoningEffort","data":{"configId":"reasoningEffort"}}` |
| `effort` | `high` | error `-32602 "Invalid params: Unknown config option: effort"` data `{"configId":"effort"}` |
| `reasoning_effort` | `high` | **accepted** `result {}` → echo `reasoning_effort: "high"` |
| `autonomy` | `high` / `skip-permissions-unsafe` / `bypassPermissions` | error `-32602 "Invalid params: Unknown config option: autonomy"` (all three values) |
| `mode` | `high` / `skip-permissions-unsafe` / `bypassPermissions` | error `-32602 "Invalid params: Unknown config option: mode"` (all three) |
| `auto` | `high` / `skip-permissions-unsafe` / `bypassPermissions` | error `-32602 "Invalid params: Unknown config option: auto"` (all three) |

Valid option ids are exactly `autonomy_level`, `model`, `reasoning_effort` — the ones declared in the session/new result.

### P2b — autonomy_level and invalid values (fresh process)

| configId | value | result |
|---|---|---|
| `autonomy_level` | `auto-high` | **accepted** `result {}` |
| `autonomy_level` | `bypassPermissions` | error `-32602 "Invalid params: Invalid autonomy level value: bypassPermissions"` data `{"configId":"autonomy_level","value":...}` |
| `autonomy_level` | `no-such-level` | error `-32602 "Invalid params: Invalid autonomy level value: no-such-level"` |
| `model` | `no-such-model` | error `-32602 "Invalid params: Invalid model: no-such-model"` |
| `model` | `gpt-5.6` (not in catalog) | error `-32602 "Invalid params: Invalid model: gpt-5.6"` |
| `reasoning_effort` | `turbo` | error `-32602 "Invalid params: Invalid reasoning effort value: turbo"` |

Error taxonomy: unknown id → `Unknown config option: <id>` (data `configId`); known id with bad value → `Invalid <name> <value>: <value>` (data `configId`+`value`).

## P3 — session/prompt to completion

`session/prompt {"sessionId":sid,"prompt":[{"type":"text","text":"Reply with exactly: pong"}]}`. Full event sequence:

```
send session/prompt (id 3)
recv session/update current_mode_update    (currentModeId auto-high)
recv session/update available_commands_update
recv session/update config_option_update  (full 3-option snapshot)
recv session/update agent_message_chunk    content.text "pong"
recv {"jsonrpc":"2.0","id":3,"result":{"stopReason":"end_turn"}}
```

Reply text: `pong`. Turn termination is a JSON-RPC response to the prompt request with `result.stopReason` (`end_turn` here); no separate stop notification. `sessionId` appears in every `session/update` `params`.

## P4 — session resume / load / list

Native session-id surface: `session/new` result `sessionId` (primary); `session/update` `params.sessionId`; `session/list` `sessions[].sessionId`. **Neither `session/resume` nor `session/load` echoes `sessionId` in its result**, and the prompt stop response carries no session id.

- `session/resume {"sessionId":<sid>,"cwd":<repo>,"mcpServers":[]}` → **works**. Result keys `models`, `modes`, `configOptions` — the saved session selection: `model gpt-5.6-sol`, `reasoning_effort high`, `autonomy_level auto-high` (retained). Advertised via `sessionCapabilities.resume` (holder-preferred method).
- `session/load` same params → **also works**. Result keys `configOptions` only (same currents). Advertised via `loadSession: true`.
- `session/list {"cwd":<repo>}` → **works** (cwd-scoped, paginated via `nextCursor`). Only sessions that had ≥1 turn are listed; entry shape:

```json
{"sessions":[{"sessionId":"2e1e97fc-88d0-4476-b9a4-600d4e124748","cwd":"/tmp/kaola-droid-acp-probe/repo",
  "title":"Pong","updatedAt":"2026-09-16T16:52:01.072Z","_meta":{"messageCount":4}}]}
```

The P3 session (prompted, then its process SIGTERM'd) persisted server-side and reappears in the list — resume-after-crash works. Sessions created but never prompted (P1/P2) do not appear.

## P5 — launch-flag shaping (write probe)

Prompt in both runs: `Create a file named probe-flag.txt containing the word ok in the current directory, then reply done.`

(a) Flagged process: `droid exec --output-format acp --skip-permissions-unsafe -m auto` (accepted with zero stderr).

- PERMISSION REQUESTS: **0**.
- Tool stream: `tool_call ApplyPatch (pending)` → `tool_call_update completed` with `rawOutput {"success":true,"files":[{"file_path":"/private/tmp/kaola-droid-acp-probe/repo/probe-flag.txt","display_operation":"create","content":"ok"}]}`.
- File written: `probe-flag.txt` exists, content `ok`.
- Reply: `Done.`; stop `end_turn`.
- Session config at session/new: `model gpt-5.6-sol`, `autonomy_level auto-high`, `reasoning_effort high` — **identical to the no-flag defaults**; `-m auto` did not change the session model.

(b) Control process: plain `droid exec --output-format acp`, same prompt.

- PERMISSION REQUESTS: **0**.
- Same ApplyPatch stream; file written (`ok`); reply `done`; stop `end_turn`; same session config (gpt-5.6-sol / auto-high / high).

**Finding: the default ACP session is already full bypass.** `autonomy_level` defaults to `auto-high` ("Auto-approves all actions") with no flags and no config calls, so `--skip-permissions-unsafe` and `-m auto` are accepted but shape nothing observable in the ACP session — same model, same autonomy, same permission behavior, same write outcome.

## P6 — config-option route

Plain process; before the prompt, applied `set_config_option model=auto` and `set_config_option autonomy_level=auto-high` — both `result {}`, each followed by a `config_option_update` echo. Then the P5 write prompt:

- PERMISSION REQUESTS: **0** (config-option-asserted autonomy also yields full bypass; bypass is additionally already the default).
- Write outcome: the transcript contains two consecutive identical driver cycles (a transient double-execution of the probe command by the shell harness; both cycles 0 permission requests). Cycle 1 (model=auto) picked a terminal `execute` (`printf 'ok\n' > .../probe-flag.txt`, kind execute, riskLevel medium) that reported completed but produced no observable file at check time; cycle 2 applied `ApplyPatch` and `rawOutput success:true` with the file create — `probe-flag.txt` contents `ok` confirmed on disk afterward. The ApplyPatch path (also default under `gpt-5.6-sol`) writes reliably; the terminal-execute variant (selected under model=auto) is the only flaky write observed.
- Reply text `done`; stop `end_turn`.

## Conclusions

1. **Config-option declarations live in the `session/new` result, not `initialize`.** Three `select` options: `autonomy_level` (normal/spec/auto-low/auto-medium/auto-high), `model` (49 catalog ids incl. `auto`), `reasoning_effort` (none/low/medium/high/xhigh/max). `config_option_update` notifications echo full option state on change and at prompt start; there is no `currentSessionConfigOption` field.
2. **`session/set_config_option` works.** Param shape `sessionId` + `configId` + `value`; accepted → `{}` result; unknown id → `-32602 Unknown config option: <id>`; invalid value → `-32602 Invalid <thing> value: <value>`.
3. **Droid ACP sessions default to full bypass**: `autonomy_level=auto-high` from session/new onward, no flags or config required. Launch flags `-m auto` and `--skip-permissions-unsafe` are accepted but have no observable effect on the ACP session (identical config currents, identical 0-permission behavior, identical write).
4. **Bypass evidence**: 0 `session/request_permission` in the flagged run, the no-flag control, and the config-option run; file write succeeded in all three (via ApplyPatch).
5. **Resume**: both `session/resume` (advertised `sessionCapabilities.resume`) and `session/load` (`loadSession`) work and return the saved selection (models/modes/configOptions). Neither echoes the sessionId; the Runner's captured `session/new` `sessionId` is the id to resume. `session/list` (cwd-scoped) lists only sessions with ≥1 turn.
6. **Effective-model evidence** for an ACP session: session/new result (`configOptions.model.currentValue`, `models.currentModelId`), resume/load results, and `config_option_update` echoes. Observed default/effective: `model=gpt-5.6-sol`, `reasoning_effort=high`, `autonomy_level=auto-high`. Selecting a different model resets `reasoning_effort` to `none` (apply order model→effort, which the Runner already uses).
7. **Effective model is NOT pinned by launch flags** (`-m auto` left the session at `gpt-5.6-sol`); to pick a model, use `set_config_option model=<catalog id>` (or accept the seat default).
8. **Process lifecycle**: `droid exec --output-format acp` persists across turns (does not exit after `end_turn`), exits rc=0 on SIGTERM. All 11 spawned pids verified gone; no orphaned children; remaining `droid` processes are pre-existing Factory.app worker/daemon processes unrelated to this probe.
9. **Code-level gap for the Runner's mode assert**: `kaola-acp.py` hardcodes `config_id = "mode"` for `ACP_SKIP_MODE` platforms. Droid's option id is `autonomy_level`, so `--mode` on droid would fail with `Unknown config option: mode` and droid must not be added to the current `ACP_SKIP_MODE` dict as-is.

## Recommended manifest facts (platforms/droid.yaml)

- `acp_command`: **`droid exec --output-format acp`** (bare; no `-m auto` / `--skip-permissions-unsafe` — accepted but no observable ACP effect; defaults already give model `gpt-5.6-sol` and full bypass).
- `acp_model_config_id`: **`model`** (values must be catalog ids; `auto` is valid).
- `acp_effort_config_id`: **`reasoning_effort`** (`effort`/`reasoningEffort` are rejected); values none/low/medium/high/xhigh/max.
- `acp_fast_config_id`: **`""` (none)** — no fast option advertised; fast rides model variants (`gpt-5.6-sol-fast`, `claude-opus-5-fast`, …) → `fast_support: "model-variant"`.
- ACP permission/mode bypass: optionId **`autonomy_level`**, value **`auto-high`**. Bypass is already the session default on 0.220.0; to assert it explicitly, add an `acp_mode_config_id: "autonomy_level"` manifest key (new) and `ACP_SKIP_MODE["droid"] = "auto-high"` — until the Runner's mode config_id is manifest-driven, do NOT put `droid` in `ACP_SKIP_MODE` (it would send `configId "mode"`, which droid rejects).
- `default_model_id`: `gpt-5.6-sol` (seat default; catalog-valid). `default_model_parameters`/`default_model_effort`: `high`.
- `resume_syntax` / continue: native `session/resume` works (holder-preferred); resume id = the `session/new` result `sessionId` persisted in the record; `session/list` is cwd-scoped and lists only sessions with ≥1 turn.
- `acp_client_capabilities`: `"terminal:false,fs:false"` (what the holder already sends; agent `_meta` advertises `terminal_output:true`, `terminal-auth:true`).
- `acp_verified_versions`: `cli=0.220.0;protocol=1`.
