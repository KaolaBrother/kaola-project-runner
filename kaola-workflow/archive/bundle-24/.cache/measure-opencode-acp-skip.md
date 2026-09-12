# OpenCode ACP skip-all / auto-approve measurement

Question: does OpenCode ACP expose any skip-all / auto-approve permission knob that default `start` can apply so `send --wait` does not hang on unanswered `session/request_permission`?

`measured_skip_exists: no`

No ACP argv, env advertised on `acp`, or `configOptions` value is skip-all. TUI `--auto` is not an ACP knob. `configOptions.mode` is agent identity (`build` / `plan`). Live `session/set_config_option` rejects skip-shaped values.

This record does not choose skip vs PTY-bypass.

## Environment

- Date (UTC): `2026-09-12T16:48:43Z`
- Host: macOS darwin-arm64
- Binary: `/Users/ylpromax5/.local/node-v24.14.0-darwin-arm64/bin/opencode`
  - realpath: `/Users/ylpromax5/.local/node-v24.14.0-darwin-arm64/lib/node_modules/opencode-ai/bin/opencode.exe`
- `opencode --version` → `1.18.29` (exit 0)
- python3: 3.13.12
- Repo cwd for ACP probe: `/Users/ylpromax5/Workspace/kaola-project-runner`
- User config read only: `~/.config/opencode/opencode.json` (not mutated)
- Public schema: `https://opencode.ai/config.json` (fetched 200 with browser UA; 403 without)
- No `man opencode`
- Leftover `opencode acp` processes after probes: none

## Commands and observations

Observations are labeled with the exact command. Stderr/stdout trimmed to proving lines.

### 1. CLI surface

**Command:** `opencode --help` (exit 0)

Proving lines (TUI / default command options):

```
      --auto          auto-approve permissions that are not explicitly denied (dangerous!)
                                                                          [boolean] [default: false]
      --mini          start the minimal interactive interface             [boolean] [default: false]
```

`--auto` and `--mini` appear on the default TUI command, not on `acp`.

**Command:** `opencode acp --help` (exit 0)

```
opencode acp

start ACP (Agent Client Protocol) server

Options:
  ...
      --cwd          working directory
```

ACP extra option is `--cwd` only. No `--auto`, `--mini`, `--yolo`, permission-mode, or skip flag.

**Command:** `opencode run --help` (exit 0)

```
      --auto         auto-approve permissions that are not explicitly denied (dangerous!)
                                                                          [boolean] [default: false]
```

`run` has `--auto`. `opencode acp --help --show-hidden` still has no auto/yolo/danger lines.

**Command:** `opencode help acp` (exit 1) — prints the top-level help (same as `opencode --help`), not the ACP subcommand help.

Closed-stdin subprocess tests (`stdin=DEVNULL`, kill after 1.5s if needed):

| argv | extra env | exit | hung | proving stderr |
| --- | --- | --- | --- | --- |
| `acp --auto` | — | 1 | no | reprints `opencode acp` help (unknown option; no `--auto` listed) |
| `acp --yolo` | — | 1 | no | same help reprint |
| `acp --dangerously-skip-permissions` | — | 1 | no | same help reprint |
| `acp --mini --auto` | — | 1 | no | same help reprint |
| `acp --always-approve` | — | 1 | no | same help reprint |
| `acp --skip-permissions` | — | 1 | no | same help reprint |
| `acp --permission-mode bypass` (and `bypassPermissions`, `yolo`) | — | 1 | no | same help reprint (earlier batch) |
| `acp --yes` / `--approve` / `--bypass` / `--auto-approve` / `--alwaysApprove` | — | 1 | no | same help reprint (earlier batch) |
| `--auto acp` | — | 0 | no | `Error: Failed to change directory to /Users/ylpromax5/Workspace/kaola-project-runner/acp` |
| `--mini --auto acp` | — | 1 | no | `Error: --mini requires a TTY stdout` |
| `acp` | `OPENCODE_YOLO=1` | 0 | no | empty; process exits because stdin is already closed |
| `acp` | `OPENCODE_PERMISSION={"*":"allow"}` | 0 | no | empty; same stdin-closed exit |

`opencode --auto acp` treats `acp` as the TUI `project` positional, not the ACP subcommand.

Binary strings (TUI builder, not ACP):

```
.option("auto",{type:"boolean",describe:"auto-approve permissions that are not explicitly denied (dangerous!)",default:!1})
.option("yolo",{type:"boolean",hidden:!0,default:!1})
.option("dangerously-skip-permissions",{type:"boolean",hidden:!0,default:!1})
...
args:{..., auto:D.auto||D.yolo||D["dangerously-skip-permissions"]}
```

ACP builder in the same binary:

```
{command:"acp",describe:"start ACP (Agent Client Protocol) server",
 builder:(D)=>{return Ou(D).option("cwd",{describe:"working directory",type:"string",default:process.cwd()})},
 handler: ... process.env.OPENCODE_CLIENT="acp"; ...}
```

ACP command sets `OPENCODE_CLIENT=acp` and does not register `--auto`/`--yolo`.

### 2. Config / env

**Read (not mutated):** `~/.config/opencode/opencode.json`

Top-level keys used here: `"$schema": "https://opencode.ai/config.json"`, `"permission": "allow"`. Other fields (mcp/provider/model) exist; secrets not copied into this record.

**Command:** `opencode debug config` (resolved config; permission slice only)

User `"permission": "allow"` resolves to:

```
  "permission": {
    "*": "allow"
  }
```

**Command:** `OPENCODE_PERMISSION='{"bash":"deny"}' opencode debug config`

Merge overlay (proves env is a config overlay, not an ACP protocol field):

```
  "permission": {
    "*": "allow",
    "bash": "deny"
  }
```

Invalid `OPENCODE_PERMISSION=not-json` leaves `{"*":"allow"}` (warning path in binary: skip invalid JSON).

`OPENCODE_PERMISSION='"allow"'` (JSON string) is merged as object spread (`"0":"a"` …) — the overlay expects a JSON object, not the schema's string enum.

**Fetched schema** `https://opencode.ai/config.json` (`PermissionActionConfig` enum): `"ask" | "allow" | "deny"`.

`Config.properties.permission` → `PermissionConfig` (global string or per-tool rules). No schema field named yolo / skip-all / auto-approve / bypassPermissions.

`AgentConfig.properties.mode` enum is `"subagent" | "primary" | "all"` (agent class), not skip-all.

**Command:** `opencode agent list` / `opencode debug agent build`

Native agents include `build (primary)` and `plan (primary)`. `build` description: "The default agent. Executes tools based on configured permissions." Even with global `* allow`, resolved `build` rules still include `doom_loop`/`external_directory` `ask` (and later overlapping `* allow` entries). This is agent permission policy, not an ACP skip mode.

**Env names in the binary matching perm/auto/acp:** `OPENCODE_PERMISSION`, `OPENCODE_ACP_PROFILE`, `OPENCODE_AUTO_HEAP_SNAPSHOT`, `OPENCODE_AUTO_SHARE`, `OPENCODE_DISABLE_AUTOCOMPACT`, `OPENCODE_DISABLE_AUTOUPDATE`.

- `OPENCODE_ACP_PROFILE==="1"` is ACP profiling, not permissions.
- `OPENCODE_PERMISSION` JSON-parses into `config.permission` for every OpenCode client including ACP (same Config.load path). It is not listed in `opencode acp --help`.
- No `OPENCODE_AUTO` / `OPENCODE_YOLO` identifiers in the binary env table.

TUI palette (not ACP): `permission.mode` toggle titled "Enable auto-approve permissions" when `M.permission.mode==="auto"`. That is the TUI `--auto` state, not `configOptions`.

### 3. ACP protocol

Short-lived subprocess (no kaola session / no holder leftover):

```
opencode acp --cwd /Users/ylpromax5/Workspace/kaola-project-runner
```

JSON-RPC: `initialize` (id 1) then `session/new` (id 2), then `session/set_config_option` probes, then SIGTERM. Raw dump: `/tmp/opencode-acp-handshake.json`.

**initialize result**

- `protocolVersion`: 1
- `agentInfo`: `{name: OpenCode, version: 1.18.29}`
- `agentCapabilities`: `loadSession`, `mcpCapabilities`, `promptCapabilities`, `sessionCapabilities` (`close`/`fork`/`list`/`resume`)
- No initialize field that is skip-all / auto-approve / permission-mode
- `authMethods`: `opencode-login` present; `session/new` still succeeded (`login_required` not blocking this probe)

**session/new result** `configOptions` (ids only; values summarized):

| id | name | category | type | currentValue | option values |
| --- | --- | --- | --- | --- | --- |
| `model` | Model | model | select | `zhipuai-coding-plan/glm-5.3` | provider/model ids (catalog) |
| `effort` | Effort | thought_level | select | `low` | `low`, `high`, `max` |
| `mode` | Session Mode | mode | select | `build` | `build` ("The default agent. Executes tools based on configured permissions."), `plan` ("Plan mode. Disallows all edit tools.") |

No `permission` configOption. Mode values are agent identities, not skip-all.

**session/set_config_option probes** (same session `ses_f697b7ff4ffeTfChkkzOenRPo4`):

| configId | value | response |
| --- | --- | --- |
| `mode` | `yolo` | `-32602` `Invalid params: mode not found: yolo` |
| `mode` | `auto` | `-32602` `mode not found: auto` |
| `mode` | `bypass` | `-32602` `mode not found: bypass` |
| `mode` | `bypassPermissions` | `-32602` `mode not found: bypassPermissions` |
| `permission` | `allow` | `-32602` `unknown config option: permission` |
| `permission.mode` | `auto` | `-32602` `unknown config option: permission.mode` |

Binary ACP permission path (when a permission event is queued):

```
var jx=[
  {optionId:"once", kind:"allow_once", name:"Allow once"},
  {optionId:"always", kind:"allow_always", name:"Always allow"},
  {optionId:"reject", kind:"reject_once", name:"Reject"}
];
if(!this.input.connection.requestPermission){ await this.reply(P.id,"reject", x.cwd); return }
await this.input.connection.requestPermission({ sessionId, toolCall, options:jx })
```

ACP does not auto-allow. Missing client `requestPermission` auto-**rejects**. Client answers `once` / `always` / `reject`. That is per-request `permit`, not a start-time skip-all.

**Live `session/prompt` that would trigger `session/request_permission`:** not run. It needs a model turn, can hang if unanswered, and this machine's resolved config already has `"*":"allow"` so a prompt would not isolate a start knob. No auto-permit invented.

### 4. PTY comparison

**Command:** `opencode --help` — `--mini` and `--auto` still exist as TUI options (quoted above).

Binary: TUI `auto` is `D.auto||D.yolo||D["dangerously-skip-permissions"]`. `opencode --mini --auto acp` is still the TUI command (`--mini requires a TTY stdout` here), not `opencode acp`.

## Observations vs inferences

### Observations

- `opencode acp --help` lists `--cwd` and shared server flags; no permission skip flag.
- `opencode acp --auto` / `--yolo` / `--dangerously-skip-permissions` / `--mini --auto` exit 1 and reprint ACP help.
- `opencode --auto acp` is TUI + project path `.../acp`.
- Live ACP `configOptions` are `model`, `effort`, `mode∈{build,plan}`.
- Skip-shaped `session/set_config_option` values fail as recorded.
- User config `"permission": "allow"` is a file-level PermissionConfig, resolved to `{"*":"allow"}`.
- `OPENCODE_PERMISSION` merges JSON into that config object (measured via `debug config`).
- ACP permission events, if raised, go to `session/request_permission` with `once`/`always`/`reject`.

### Inferences

- **(high)** OpenCode ACP 1.18.29 does not expose a skip-all / auto-approve knob equivalent to TUI `--auto` or to other platforms' ACP `mode=bypassPermissions|bypass|yolo`. Refuted if a later CLI adds an `acp` flag or a `configOptions` id/value that `session/set_config_option` accepts and that stops `session/request_permission`.
- **(high)** `configOptions.mode` is session agent identity (`build`/`plan`), not permission skip. Refuted if a mode value other than those two is accepted and documented as skip-all.
- **(medium)** `OPENCODE_PERMISSION` is a process-wide Config overlay, not an ACP-advertised start knob. Default `start` could set the env, but that is config merge (same as editing `opencode.json`), not `acp` argv / `configOptions`. Refuted if `opencode acp --help` documents it as ACP auto-approve.
- **(medium)** Global `"*":"allow"` does not prove ACP will never emit `session/request_permission`; `build` still has `ask` rules (e.g. `external_directory`, `doom_loop`). Refuted by a live prompt under this config with zero permission events for those tools — not measured here.
- **(high)** PTY still has `--mini --auto`. That knob is not accepted on `acp`.

## Conclusion

`measured_skip_exists: no`

Surfaces ruled out as ACP skip-all for default `start`:

- argv: `opencode acp --auto|--yolo|--dangerously-skip-permissions|--always-approve|--skip-permissions|--permission-mode …|--mini --auto|…`
- `opencode --auto acp` (project path, not ACP)
- ACP `configOptions` ids `model` / `effort` / `mode`
- ACP `mode` values `yolo` / `auto` / `bypass` / `bypassPermissions`
- ACP `configId` `permission` and `permission.mode`
- Env `OPENCODE_YOLO` / `OPENCODE_AUTO` / `OPENCODE_SKIP_PERMISSIONS` / `OPENCODE_AUTO_APPROVE` / `ACP_PERMISSION_MODE` as ACP CLI skip flags

Related non-ACP surfaces (not a default-start ACP skip knob): TUI/run `--auto` (hidden aliases `--yolo`, `--dangerously-skip-permissions`); file `permission` ask/allow/deny; env `OPENCODE_PERMISSION` JSON overlay.

## Unknowns

- Whether a live ACP `session/prompt` under this user config still emits `session/request_permission` (not run; would be a model turn).
- Whether `OPENCODE_PERMISSION` overlay changes ACP permission-event rate vs file config alone (only `debug config` merge was measured).
- Behavior if the ACP client omits `requestPermission` (binary path auto-rejects; not live-probed).
- Whether a future OpenCode version adds an `acp` flag; this record is for CLI `1.18.29` on 2026-09-12.
