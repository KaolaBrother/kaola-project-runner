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
carry credential/config reads (`~/.zcode/v2/config.json` and
`~/.config/zcode-acp/config.json`) and a `runtimeModel` overlay that inlines
third-party API keys on `session/setModel`. That is incompatible with
subscription-login-first Coding Plan use. Gate 2 is the selected
implementation.

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

`session/setModel` forwards `{sessionId, model, persistAsWorkspaceLastUsed:false}`
only. It never reads config, never inlines `apiKey`, and never sends a
`runtimeModel` overlay. Unknown models fail closed; the adapter does not
substitute another model.

## Removed / never implemented

quota client, tasks-index sqlite, remote hub / WebSocket listener, TUI /
martty / elicitation forms, sandbox, goal-loop, provider-registry push,
credential helpers, PATH/registry discovery, `ZCODE_MODEL` / `ZCODE_PROVIDER`
injection, postinstall, `ws`, `zcode-acp-martty`, `@agentclientprotocol/sdk`.

## Local adapter

- Entry: `scripts/kaola-zcode-acp.py`
- Hermetic backend: `tests/contract/fake-zcode-app-server.py`
- Contract: `tests/contract/test-zcode-acp-contract.py`

Run the contract with `python3 tests/contract/test-zcode-acp-contract.py`. It is not yet
invoked from `scripts/validate.sh`: this worktree is based on Issue #49 pin commit P
(`df8b85e`), and that pin allows the tracked tree to differ from content commit R
(`bbfba65`) only by the four Grok Bot pin files. Editing `validate.sh` or committing
any other path fails that gate. Wiring into `validate.sh` belongs with the
Issue #49/#50 reconcile (Mission 4), not this adapter.

The ZCode runtime path is explicit (`--zcode-entry` / `--zcode-node` or
`KAOLA_ZCODE_ENTRY` / `KAOLA_ZCODE_NODE`) and fail-closed. Native Coding Plan
login stays inside the installed runtime via `HOME` only; the adapter never
opens credential or settings files.
