# ZCode ACP protocol reference pin

Issue #51 Gate 2: this repository owns a small Python translation from the
installed ZCode private `app-server --stdio` protocol to ACP. It does **not**
vendor `william0wang/zcode-acp` TypeScript, does not install that package, and
does not fetch `@agentclientprotocol/sdk`.

## Why Gate 2

Gate 1 (a reduced pinned fork of `william0wang/zcode-acp`) was selected in the
Mission 1 `kw:research` comment, with an explicit fallback: if the reduced core
could not be isolated from quota, task-index, goal-loop, sandbox, credential
and remote surfaces, implement a Runner-owned adapter against `docs/PROTOCOL.md`.

The core handlers import those surfaces; a maintainable reduction would still
carry `~/.config/zcode-acp/config.json` reads, `ANTHROPIC_API_KEY` environment
injection and a registry push of every configured provider. Gate 2 is the
selected implementation.

Owner correction (2026-09-16): the upstream `runtimeModel` / provider-registry
overlay is the desktop App's own mechanism for handing providers to the
app-server in memory, and CLI 0.16.5 cannot create a headless session without
it. The Runner adapter therefore reuses that protocol shape (reference:
`src/config/runtime-model.ts` and `src/config/provider-registry.ts` at the pin)
but only for the one enabled GLM Coding Plan provider, without env injection,
without a full registry push and without any disk write.

## Reference (documentation only)

- Upstream: https://github.com/william0wang/zcode-acp
- Release: v0.39.0
- Commit: `80aa4e2c39909f91145dfdf6428a3867b5c61701`
- License: Apache-2.0
- Used as: `docs/PROTOCOL.md` at that commit, as the private-protocol
  reference for `scripts/kaola-zcode-acp.py`
- Vendored upstream source bytes: **none**
- Runtime npm/registry fetch: **none**

`jpalmae/zcode-acp` v0.1.0 @ `42fe149d4b501469343c01f23ba3801832306d53` remains
rejected (CLI 0.15.2 target, credential-store writes, missing lifecycle).

## Retained translation surface

ACP `initialize` / `authenticate` (no-op) / `session/new` / `session/load` /
`session/resume` / `session/list` / `session/prompt` / `session/cancel` /
`session/close` / `session/set_mode` / `session/set_config_option` mapped onto
ZCode `session/create` / `subscribe` / `send` / `stop` / `read` / `resume` /
`list` / `close` / `setMode` / `setModel` / `setThoughtLevel` and
`interaction/requestPermission` / `interaction/requestUserInput`.

`session/create`, `session/resume` (fallback after a faithful resume) and
`session/setModel` carry a `runtimeModel` overlay built read-only from the
desktop registry `~/.zcode/v2/config.json`: the enabled `*-coding-plan`
provider with `apiKey: {source: "inline"}`, `persistAsWorkspaceLastUsed:false`.
Start Plan and pay-as-you-go providers are refused; unknown models and other
providers fail closed; the adapter never substitutes a model or a provider,
never writes `~/.zcode/cli/config.json`, and never logs the credential.

Tool `input` (Issue #67, measured on CLI 0.16.5): `model.streaming` kind
`tool_call` carries `input` (`Read` used `file_path`; protocol examples use
`command` for `Bash`). `tool.updated` `scheduled` may omit `input` and set
`inputOmitted`/`inputRef` instead. The adapter caches the streaming `input`
and forwards only top-level path/command evidence as a bounded ACP `rawInput`
plus `locations` for path-like keys; extra and nested fields are dropped. It
does not follow `inputRef`, does not invent a path, and does not claim an
arbitrary command string is fully credential-scrubbed (registered adapter
secrets in copied strings are redacted; command is truncated).

## Removed / never implemented

quota client, tasks-index sqlite, remote hub / WebSocket listener, TUI /
martty / elicitation forms, sandbox, goal-loop, full provider-registry push
(`workspace/updateProviderRegistry`), `ANTHROPIC_API_KEY` env credential
helpers, PATH/registry discovery, `ZCODE_MODEL` / `ZCODE_PROVIDER`
injection, postinstall, `ws`, `zcode-acp-martty`, `@agentclientprotocol/sdk`.

## Local adapter

- Entry: `scripts/kaola-zcode-acp.py`
- Hermetic backend: `tests/contract/fake-zcode-app-server.py`
- Contract: `tests/contract/test-zcode-acp-contract.py`

- Desktop registry fixture: `tests/contract/fixtures/zcode-desktop-config.json`

Run the contract with `python3 tests/contract/test-zcode-acp-contract.py`; it is
invoked from `scripts/validate.sh`.

The ZCode runtime path is explicit (`--zcode-entry` / `--zcode-node` or
`KAOLA_ZCODE_ENTRY` / `KAOLA_ZCODE_NODE`) and fail-closed. Login stays inside the
installed ZCode App; the adapter opens only `~/.zcode/v2/config.json` and
`~/.zcode/v2/coding-plan-cache.json`, read-only, and never `credentials.json`,
`setting.json`, `tasks-index.sqlite`, `~/.zcode/cli/config.json` or
`~/.config/zcode-acp/config.json`.
