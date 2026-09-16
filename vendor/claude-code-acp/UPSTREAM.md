# Upstream notice: claude-code-acp (vendored, pinned fork)

- Upstream: <https://github.com/harukitosa/claude-code-acp>
- Pinned commit: `6c20f2802e390c80b0542247c6b9738e11efdc11` ("Support multiple concurrent sessions via ACPX_SESSION_NAME", 2026-03-18)
- License: MIT, Copyright (c) 2026 Haruki Tosa — `LICENSE` in this directory is the upstream file verbatim.
- Bundled runtime dependency: `@agentclientprotocol/sdk` 0.16.1 (Apache-2.0) with its `zod` 4.3.6 peer (MIT), pinned by `package-lock.json` and compiled into `dist/index.js`.
- Vendored by the Kaola Project Runner for Issue #50. Runtime needs only a local `node` (>= 20) and the local `claude` binary: no registry install, no `npx`, no download.

The npm registry package named `claude-code-acp` is a different, older project that depends on `@anthropic-ai/claude-code`; it is not this code and must never be referenced by the Runner.

## Build and derivation

`dist/index.js` is committed. It is produced from the vendored sources by `kaola-dist.py --write` (tsup/esbuild, single ESM file, no source map, no declarations, SDK and zod bundled). `dist/DERIVATION.json` records the sha256 of every build input, the toolchain versions, and the output hash. `kaola-dist.py --check` re-hashes the inputs and the output with no network and no `node_modules`; when the dev toolchain is installed it also rebuilds into a scratch directory and requires a byte-identical result. The build has been verified byte-identical across repeated builds on the recording machine.

Developer loop (network only for `npm ci`): `npm ci && npm test && ./kaola-dist.py --write && ./kaola-dist.py --check`.

## Local modifications (the complete list)

1. `src/config.ts` — new fields: `claudeBin` (from `CLAUDE_ACP_CLAUDE_BIN`, else `CLAUDE_BIN`; empty counts as unset), `runtimeDir` (`CLAUDE_ACP_RUNTIME_DIR`, default `os.tmpdir()`), `stateDir` (`CLAUDE_ACP_STATE_DIR`, default `~/.claude-code-acp`).
2. `src/claude-runner.ts` — exact binary: when `claudeBin` is set it must be an absolute, existing, executable regular file and is the only thing spawned (never `PATH`); otherwise the upstream bare `claude` lookup applies. Per-session `LaunchOptions` (`model`, `effort`, `permissionMode`, `fast`) are translated onto every subprocess as `--model`, `--effort`, `--permission-mode`, and the process-scoped `--settings '{"fastMode": true|false}'` pin (true only for `fast=on`), first turn and every `--resume` turn alike; `--dangerously-skip-permissions` is emitted only when no permission mode governs the session. Children spawn `detached` in their own process group; `cancel` sends SIGTERM to the group and SIGKILL after 2 s; new `shutdown()` stops every running group and removes temp files. MCP temp config is written under `runtimeDir` and removed when the consuming subprocess exits (and again on shutdown); resume turns run in the session cwd. A non-zero streaming exit rejects with the session id the CLI already announced attached as `claudeSessionId`. `sanitizeEnv()` is unchanged (drops `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN`, inherits everything else).
3. `src/session-store.ts` — persisted record version 2 (`names` for `ACPX_SESSION_NAME`, `sessions` keyed by Claude Code session id with cwd and updatedAt; a version-1 file is converted on read) under `stateDir`. `session/new` no longer auto-continues the previous conversation of the same cwd; continuity happens only through `ACPX_SESSION_NAME` or an explicit resume. New `listPersisted`, `hasPersisted`; `clearPersistedSession` takes the Claude Code session id. Log lines mask Claude Code session ids.
4. `src/agent.ts` — ACP session modes are Claude Code permission modes (`bypassPermissions` default, `acceptEdits`, `auto`, `manual`, `dontAsk`, `plan`); config options `mode`, `model`, `effort` (`low|medium|high|xhigh|max`), `fast` (`on|off`) with value validation; `thought_level` removed. `sessionCapabilities.resume` advertised and `session/resume` implemented (an ACP id of this process, or a Claude Code session id, which binds a session whose next turn runs `--resume`). `session/list` also returns persisted Claude Code sessions for the cwd. An unusable exact binary fails `session/new`, `session/resume`, and `session/prompt` with a JSON-RPC internal error instead of a chat message. MCP servers are accepted in the ACP stdio shape (`{name, command, args, env: [{name, value}]}`) as well as upstream's `transport` shape. `newSession` no longer logs the raw request (which could contain MCP env values). The resume-failure warning no longer prints the session id. A cancelled `--resume` turn (the CLI exits 143 on SIGTERM) is reported as `cancelled` and never falls back to a fresh conversation or clears the persisted session id, and a cancelled first turn persists the session id the CLI announced so the next turn resumes it (live finding, Issue #50 Mission 3). `createClaudeCodeAgent` accepts an optional runner.
5. `src/index.ts` — one shared runner; connection close, stdin end, SIGINT, and SIGTERM run `runner.shutdown()` before exit so no `claude` process or temp file outlives the bridge.
6. `tsup.config.ts` — bundle the SDK and zod (`noExternal`), `platform: "node"`, no source map, no declarations.
7. `tests/agent-modes.test.ts` — expectations updated to the permission-mode list and the `effort` option; every other upstream test file is verbatim and passes.
8. `.gitignore` — replaced: `dist/` is committed here.
9. Added: `UPSTREAM.md` (this file), `kaola-dist.py`, `dist/index.js`, `dist/DERIVATION.json`, `tests/kaola-fork.test.ts`.

Upstream files omitted from the vendored copy (documentation and planning notes that describe registry installation; see the upstream repository at the pinned commit): `README.md`, `CLAUDE.md`, `PLAN.md`, `docs/`.

## Upstream file inventory at the pinned commit

`verbatim` files must hash exactly as listed; `modified` files must differ; `omitted` files must be absent. `tests/contract/test-issue-50-claude-acp-bridge.py` checks this table.

| upstream path | status | upstream sha256 |
|---|---|---|
| `.gitignore` | modified | `b77a3cfa4e46891b5105b474d5187df005d33fd7fae6b87f38073b737346da8b` |
| `CLAUDE.md` | omitted | `a1d05c1d7c4546bf37b7d70e7b56aeb26e16fa5ee308e8d87fe106c775d37afa` |
| `LICENSE` | verbatim | `9aef7c953434dde57dc0e9f7b596651b7e2353ef2e4b04470eb8bb8238d37443` |
| `PLAN.md` | omitted | `04854d78a4343d3ee6a8b2292f70e7bab3276cfbf8c6a5cfe8716474d0bdaf8d` |
| `README.md` | omitted | `783204aa0188280d6f375cd4f614c988c1b00d3413af85f48610e9a567295092` |
| `bin/claude-code-acp.js` | verbatim | `3fa961c18fa4538b31d2c6f1ae634ac30f155bf0d307a12b62995ecd9ec584a3` |
| `docs/architecture.md` | omitted | `a3b2d256dfb355e2f3c52e6252b75d724a582b821da259e8a0776d5b2d899226` |
| `docs/configuration.md` | omitted | `3eb4c87a1b75f9139588268475645db0744ec53113063eb4be07648d1ccd801b` |
| `docs/development.md` | omitted | `222f44460e7e5696985a7e70842234390b57a29757e73ea7d004a19310b361e5` |
| `docs/jetbrains.md` | omitted | `2252a611e7d46d4894d043e9834b907e499e837e218850c0f3e99cc3221f0f1a` |
| `docs/openclaw.md` | omitted | `e43cc46be4e790256e698fbbc933331ef9d51b6cf9a72ed097e16aa94a1657eb` |
| `docs/protocol.md` | omitted | `2ced47df443e207ecf8e4e80a9b093763c15c0d79be61a75227c8cd0802fe4d9` |
| `package-lock.json` | verbatim | `f7145b99bdf8b2b60f8fbf78be47f15876edc0e6d5bd592581b59a1122394366` |
| `package.json` | verbatim | `00ef476eeb3af012c464018718450d8e79d6a6c108746ae6b4023be51c9e9119` |
| `src/agent.ts` | modified | `bfdab520429a2efbfdef8a7e12161df1c9ff72122568ba436fcca7ada2082499` |
| `src/claude-runner.ts` | modified | `a2d629c431c53cb74e46964201c6fae780c63b2f25f0c8a27fc0de84675d0ad3` |
| `src/config.ts` | modified | `fa01e77d3ed49c4849b429d88ef5bb0ee52dcb90225a9e2b474f1188196dd3ea` |
| `src/index.ts` | modified | `95a45966af0a5bf9ee3b10d5190cd9cd2b4c2de21bb5fe14a6a8325a054e6b4f` |
| `src/logger.ts` | verbatim | `3347c28e1066988a5c9aac0deac2bf0d7cbaa49e0eb807b0bdc3b34c2601e726` |
| `src/session-store.ts` | modified | `8ca8ea3e326808b1aa3bb15f5e96a3a0ae44c82b134bdecfae84c0d8435e015a` |
| `src/validation.ts` | verbatim | `ebdeac56090f38a71a600601ee34dab9c16ecedb05e63a2fba159d9fd078fe0e` |
| `tests/agent-cancel.test.ts` | verbatim | `08156c30ccf2f9c975358cac2128ec35b67eee57e92764dd43302b2a21ebcbbf` |
| `tests/agent-errors.test.ts` | verbatim | `9170a4a873eb416e099bd0eb5377e1b7a0ce254aeb6a7d0e0b552372d0cf3f9e` |
| `tests/agent-modes.test.ts` | modified | `c5a7518e99c9af2273c57359748846debbdc2ad862304534fa2c499c8306d659` |
| `tests/agent-streaming-updates.test.ts` | verbatim | `9d42056ab052773d73e99427eecffeb5d60f0488ed6f7c7f4d9ea94d923aa294` |
| `tests/agent-tool-call.test.ts` | verbatim | `000c1fdee58c782ef06c183eaf36b712eb7de074d5e67e797068e9a1ade13ee2` |
| `tests/agent.test.ts` | verbatim | `032600b51a2555c5c810643b18e9246d5d28f00d6eb3557475f1fc32fb18524d` |
| `tests/claude-runner-config.test.ts` | verbatim | `98e0db3279aa691c09a1ed7f973807121945388575e272973f7cd4180b78d6d1` |
| `tests/claude-runner-env.test.ts` | verbatim | `ccbdac597f06a6e55dff9fb18ad2344aa2adbee712c18a4b8aaaac2525417900` |
| `tests/claude-runner-masking.test.ts` | verbatim | `50ab322e62d91f4781ccbe15b2dcf07c61f6ebd58b533a59d83e94e18727b7c0` |
| `tests/claude-runner.test.ts` | verbatim | `b7f384b44f336592a0ab10266da43bb1f405a8cae901e50f245694ac23e2511e` |
| `tests/config.test.ts` | verbatim | `4029fbd0bb038ff255711e6352a82da7cf3504dbf8d2722cc3d107794ac688cc` |
| `tests/e2e.test.ts` | verbatim | `f737ce74fc8672d1ae930567d07d057667a104adc198f69a44008ef1ce5e500d` |
| `tests/logger.test.ts` | verbatim | `d07698f0482c9071b648ee7aa5a57a85d0b5d452ce6735adece561c412eed7de` |
| `tests/mcp-passthrough.test.ts` | verbatim | `99d634c53a97950dcdbd7d9584c3c07d282c0805ab5e74c8666c3e34558a54ab` |
| `tests/request-permission.test.ts` | verbatim | `6570d7a0590d49b08a152b6bf8dc7a8cdc0c000905ac0c3c55186e6889738ed2` |
| `tests/session-store-extended.test.ts` | verbatim | `1c3c7ae97cb15221caa45f34b0cbb654ac7bb1dddad8305497d6d1160ed1e0c0` |
| `tests/session-store.test.ts` | verbatim | `07115488fe322af92e03f1c2f912c44734d0f536fb7ed9a823578475aa6f4f48` |
| `tests/streaming-thinking.test.ts` | verbatim | `6a6e8cfe5ff042274cc7ac9068be23f03613c8b1a98019bb90060931fa3d1e24` |
| `tests/streaming.test.ts` | verbatim | `8ca5e28f4ea6471ab5ef602ccb962811fdb776ce67ee243e0044d2623fefc576` |
| `tests/validation.test.ts` | verbatim | `86cbf9ee1e65cbce635d0833d06d2775209e9790110a7b359bdc110d003c7c74` |
| `tsconfig.json` | verbatim | `b6e707efcf77a4a999b6250bf06d88cbfe80caecafdfda01bf83339a6d619766` |
| `tsup.config.ts` | modified | `46fc2490297decd1a102a9c5b9f15cbe7c5f381531e99113f571a352ceb40546` |
