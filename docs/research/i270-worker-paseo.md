# READ-ONLY web source review — issue #270

**Target:** https://github.com/getpaseo/paseo
**Branch:** `main`
**Recorded commit SHA:** `8f1091da64f660827f38512cbbd073357445b138` (main tip at review time, author date 2026-10-07)
**Recorded tree SHA:** `ce2cbf0bf5802bb615aada6ced0cba4a2806a0b1`
**Method:** GitHub REST (`git/trees?recursive=1`) + `raw.githubusercontent.com` at the recorded commit SHA. No clone, no install, no build, no writes outside `/tmp`.
**Local scratch:** `/tmp/kpr-i270-tree.json`, `/tmp/kpr-i270-src/` (raw file copies used for line references).
**Scope:** (A) how a plugin is declared and loaded (manifest + entry code), (B) daemon core interfaces in `packages/server` (session/workspace/provider abstractions, WebSocket/MCP surface).

Line numbers below are from the files as fetched at the recorded commit SHA and may drift on later `main`.

---

## A. Plugin declaration and loading

### Fact P1 — A plugin is declared by one `paseo-plugin.json` manifest (id required; entries are separate files)
`packages/server/src/server/plugins/manifest.ts`

- `MANIFEST_FILENAME = "paseo-plugin.json"`; `readPluginManifest(directory)` throws `Plugin manifest is missing` if the file is absent, else `PluginManifestSchema.parse(JSON.parse(...))` and `validatePluginRequirements`.
- `PluginManifestSchema` (Zod, non-strict object) fields: required `id` (`PluginIdSchema`), optional `name`, `description`, `icon` (relative `.png` inside the package), `media` (relative paths or HTTPS URLs), `requirements` (`{ paseo?: string }`, `.strict()`), and `build` (array of non-empty argv arrays; shell strings rejected).
- Example minimal manifest (test fixture, one line): `packages/app/e2e/support/fixtures/acp-chunks-plugin/paseo-plugin.json`
  `{ "id": "acp-chunks-test", "requirements": { "paseo": ">=0.8.0" } }`
- The CLLI `plugin init` scaffold writes the same shape: `packages/cli/src/commands/plugin/scaffold.ts` (`scaffoldPluginDirectory`) emits `paseo-plugin.json`, `package.json`, `tsconfig.json`, `index.client.tsx`, `index.server.ts`, `shared/`, `server/`, `client/`. Generated `paseo-plugin.json` = `{ id, "$comment": ..., media: [], requirements: { paseo: ">=<cli version>" } }`.

### Fact P2 — Entry code is one optional file per runtime: `index.server.ts` and `index.client.tsx`
`packages/server/src/server/plugins/runtime.ts`

- `CLIENT_ENTRY_FILENAMES = ["index.client.ts", "index.client.tsx"]` (line 40)
- `SERVER_ENTRY_FILENAMES = ["index.server.ts", "index.server.tsx"]` (line 41)
- `resolveEntryPaths(directory)` (line 277) resolves both; at least one must exist. A legacy `index.ts/index.tsx` is refused with a v0.8 migration error, and missing entries throw `Plugin entry points are missing: ...`.

### Fact P3 — Server entry default-exports `contribute(server)` and returns a cleanup function
`packages/plugin/src/server/contracts.ts`

- `PluginServerContribution = (server: PluginServerContext) => PluginCleanup`
- `PluginServerContext extends PluginLifecycleRegistration` and exposes `registerSettings(...)`, `handle(contract, handler)` (typed RPC), `registerProvider(provider)`, `registerUsageSource(source)`.
- Concrete server entry (fixture): `packages/app/e2e/support/fixtures/acp-chunks-plugin/index.server.ts`
  `export default function contribute(server: PluginServerContext) { server.registerProvider(runAcpProvider({ id: "acp-chunks", label: "ACP chunks", connector: connect })); return () => {}; }`
- Concrete server entry (CLI scaffold template): `server.handle(greetingRpc, createGreeting)`.
- Host-provided SDK specifiers kept external in author bundles: `packages/server/src/server/plugins/plugin-sdk-specifiers.ts` — `@getpaseo/plugin`, `@getpaseo/plugin/server`, `/server/provider`, `/server/usage`, `/server/acp`, `/client`, `/client/ui`, `/client/react-native`.

### Fact P4 — Loading pipeline: compile with esbuild, then run the server bundle in a forked child over IPC
- `packages/server/src/server/plugins/compiler.ts`: `SERVER_HOST_MODULES = [...PLUGIN_SDK_SPECIFIERS, "zod"]` (line 13); `compilePlugin(entryPaths)` (line 424) produces `{ serverBundle, clientBundle }`. Fixed host modules stay external; runtime boundary checks reject undeclared cross-boundary imports.
- `packages/server/src/server/plugins/runtime.ts`: `spawnPluginChild()` uses `fork(resolveWorkerUrl(), [], { serialization: "advanced", stdio: ["ignore","pipe","pipe","ipc"] })`; `PluginRuntime.startPlugin(pluginId, configuredPath, canPublish)` (line 327) loads manifest → resolves entries → compiles → launches. `startBuiltinPlugin` (line 346) loads in-process via `InternalPluginChild(evaluateBundle(...))` instead of a forked child. `catalog()` returns `{ id, clientBundle, requirements }` per running plugin; `invoke(...)` (line 509) is the RPC path.
- `packages/server/src/server/plugins/plugin-process.ts`: `export function createPluginWorker(...)` (line 36) is the child-side worker; `PluginWorkerChannel` is its transport.

### Fact P5 — Host↔plugin process protocol is a typed JSON-RPC-ish union (`initialize`/`ready`, `invoke`/`result`, `provider.*`, `paseo_frame`)
`packages/server/src/server/plugins/plugin-process-protocol.ts`

- `PluginProcessRequest` (host→plugin) variants: `initialize` (`pluginId, bundle, appVersion, pluginDirectory, settingsDirectory?`), `invoke` (`requestId, method, input`), `hook`/`hook.cancel`, `usage.fetch`, `usage.discover`, `provider.status`, `provider.catalog_key`, `provider.connect`, `provider.send`, `provider.close`, `shutdown`, `paseo_frame`, `paseo_close`.
- `PluginProcessMessage` (plugin→host) variants: `ready` (`methods, providers, usageSources?, hooks?`), `result`, `error`, `fatal`, `provider.connected/connect_failed/accepted/rejected/event/closed`, `settings.changed`, `hooks.changed`, `paseo_frame`, `paseo_close`.
- Both have matching Zod schemas (`PluginProcessRequestSchema`, `PluginProcessMessageSchema`) used at the boundary.

### Fact P6 — A plugin's own daemon connection is a virtual WebSocket bridged through the child IPC
- `PluginRuntime` exposes `attachPluginSocket(pluginId, socket: PluginSessionSocket)` via `PluginPaseoSessionHost` (`runtime.ts` line 204); the daemon-side implementation is `VoiceAssistantWebSocketServer.attachPluginSocket(pluginId, ws)` in `packages/server/src/server/websocket-server.ts` (line 1013), which attaches with `OWNER_SESSION_ADMISSION`.
- `PluginSessionSocket` (`packages/server/src/server/plugins/session-socket.ts`) implements a `ws`-like surface (`readyState`, `bufferedAmount`, `send`, `receive`, `close`, `on`/`once`) and converts frames to `{ type: "paseo_frame" }` / `{ type: "paseo_close" }` IPC messages.
- `packages/server/src/server/plugins/daemon-transport.ts` (`createPluginDaemonTransportFactory`) adapts the same IPC frames into the `@getpaseo/client` daemon transport (`onMessage`/`onOpen`/`onClose`), so plugin server code talks to the daemon over the same session protocol.
- Plugin `clientId` is namespaced and reserved: `packages/server/src/server/plugins/plugin-session-identity.ts` (`createPluginClientId`, `isPluginClientId`), enforced in `handleHello` (websocket-server.ts ~line 1596).

---

## B. Daemon core interfaces (`packages/server`)

### Fact S1 — Daemon assembly: `createPaseoDaemon` → `PaseoDaemon` with start/stop and wired subsystems
`packages/server/src/server/bootstrap.ts`

- `PaseoDaemonConfig` (line 390) includes `listen`, `paseoHome`, `agentClients: Partial<Record<AgentProvider, AgentClient>>`, `pluginsEnabled`, `plugins: Record<string, PluginSource>`, `mcpEnabled`, `mcpInjectIntoAgents`, relay/service-proxy settings, auth, speech/voice.
- `PaseoDaemon` (line 468): `{ config, agentManager, agentStorage, terminalManager, serviceProxy, scriptRuntimeStore, browserToolsBroker, start(), stop(), getListenTarget(), getServerId() }`.
- `createPaseoDaemon(...)` (line 580). Lifecycle start/stop from CLI: `packages/server/src/server/daemon-instance.ts` (`startDaemonInstance` line 206, `stopDaemonInstance` line 140, `waitForDaemonReady` line 59).

### Fact S2 — `Session` is the per-connection state machine; it is transport-agnostic (no WebSocket knowledge)
`packages/server/src/server/session.ts`

- Doc comment (line 635): "Session represents a single connected client session. It owns all state management, orchestration logic, and message processing. Session has no knowledge of WebSockets - it only emits and receives messages."
- `export class Session` (line 673).
- `export interface SessionOptions` (line 441) is the daemon-injected dependency surface: `clientId`, `permissions`, `onMessage(msg: SessionOutboundMessage)`, `onMessageToSource`, `onBinaryMessage`, `agentManager`, `agentStorage`, `projectRegistry`, `workspaceRegistry`, `creationService`, `scheduleService`, `checkoutDiffManager`, `workspaceGitService`, `pluginRuntime` (a large typed facade over PluginService), `mcpBaseUrl`, `terminalManager`, `providerSnapshotManager`, `paseoHome`, etc.
- `export type SessionLifecycleIntent = { type: "shutdown" | "restart"; clientId; requestId; reason }` (line 564) — daemon restart/shutdown `session_request`s are surfaced as intents to the bootstrap.

### Fact S3 — The session wire protocol is a large Zod discriminated union, enveloped for WebSocket
`packages/protocol/src/messages.ts` (re-exported/typed by `packages/server/src/server/messages.ts`)

- `SessionInboundMessageSchema` (line 3173) — client→daemon requests, e.g. `fetch_agents_request`, `create_agent_request`, `send_agent_message_request`, `fetch_workspaces_request`, `plugin_*_request`, `daemon_*_request`, schedule/loop/hub requests.
- `SessionOutboundMessageSchema` (line 6811) — daemon→client events/responses, e.g. `agent_update`, `workspace_update`, `assistant_chunk`, `plugin_*_response`, `status`, `agent_timeline_append_response`.
- `WSHelloMessageSchema` (line 7501): `{ type: "hello", clientId, clientType: "mobile"|"browser"|"cli"|"mcp"|"hub", protocolVersion, auth?: {kind:"password"|"localCredential"}, appVersion?, capabilities? }`.
- `WSInboundMessageSchema` (line 7559) = ping | hello | recording_state | `{type:"session", message: SessionInboundMessage}`. `WSOutboundMessageSchema` (line 7566) = pong | `{type:"session", message: SessionOutboundMessage}` | `hello.rejected`.
- Helpers `extractSessionMessage` / `wrapSessionMessage` (line 7595). `packages/server/src/server/messages.ts` adds `serializeAgentSnapshot` and `serializeAgentStreamEvent` (normalizes `attention_required`).

### Fact S4 — WebSocket server: `VoiceAssistantWebSocketServer` on `ws`, path `/ws`, hello+admission handshake
`packages/server/src/server/websocket-server.ts`

- `export class VoiceAssistantWebSocketServer` (line 525).
- `createWebSocketServer(...)`: `new WebSocketServer({ server, path: "/ws", handleProtocols: selectWebSocketProtocol(protocols, password), verifyClient: ... })`; origin/host are validated in `verifyWsUpgrade`; connections are refused with 503 while not `accepting` (~line 821).
- Handshake constants: `WS_PROTOCOL_VERSION = 1`, closes `4401` auth failed, `4001` hello timeout (`HELLO_TIMEOUT_MS = 15_000`), `4002` invalid hello, `4003` incompatible protocol; `EXTERNAL_SESSION_DISCONNECT_GRACE_MS = 90_000` for resumable external sessions.
- `handleHello(...)` (line 1561) → `admitPendingHello(...)` (line 1674) resolves `password` / `localCredential` (`resolveSessionAdmission`), then creates either a `reconnectable` connection (keyed by `sessionConnectionKey(principalId, clientId)` for resume) or an `ephemeral-plugin` connection.
- Public attach entry points: `attachExternalSocket(ws, metadata?, admission?, initialHello?)` (line 1001) and `attachPluginSocket(pluginId, ws)` (line 1013).

### Fact S5 — Provider abstraction: `AgentClient` / `AgentSession` with string provider ids and a registry builder
- `packages/server/src/server/agent/agent-sdk-types.ts`: `type AgentProvider = string` (line 22); `interface AgentSession` (line 657) — `run`, `startTurn`, `steerActiveTurn?`, `subscribe`, `streamHistory`, `getRuntimeInfo`, `getAvailableModes`/`setMode`, `getPendingPermissions`/`respondToPermission`, `describePersistence`, `interrupt`, `close`, `listCommands?`, `setModel?`, `setThinkingOption?`, revert variants; `interface AgentClient` (line 739) — `createSession`, `resumeSession`, `getCatalogCacheKey?`, `fetchCatalog`, `resolveConfiguredModel?`, `resolveDefaultModeId?`, `listCommands?`, `listFeatures?`, `listImportableSessions?`, `importSession?`, `isAvailable`, `getDiagnostic?`, `archiveNativeSession?`/`unarchiveNativeSession?`, `shutdown?`.
- `packages/server/src/server/agent/provider-registry.ts`: `buildProviderRegistry(logger, { pluginProviders?, runtimeSettings?, providerOverrides? })` (line 905) merges built-ins (ACP, Claude, Codex, OpenCode, Cursor, Copilot, Kimi, Kiro, Pi, OMP, Trae, etc. under `agent/providers/`) with plugin-registered providers, rejecting id conflicts with a built-in.
- Plugin version of the same contract: `packages/plugin/src/server/provider.ts` — `PROVIDER_PROTOCOL_VERSION = 1`, `PROVIDER_CAPABILITIES` (`prompt.*`, `session.*`, `permission*`, `timeline.plugin`, ...), `ProviderRegistration` (`id`, `label`, `connect`, optional `command`, `status`, `getCatalogCacheKey`), `ProviderConnection` (`version`, `capabilities`, `send`, `onEvent`, `close`). `runAcpProvider(...)` (`packages/plugin/src/server/acp.ts`) returns a `ProviderRegistration` from an ACP command or connector.

### Fact S6 — Workspace/project abstraction: registry interfaces with file-backed implementations
`packages/server/src/server/workspace-registry.ts`

- `interface ProjectRegistry` (line 131): `initialize`, `existsOnDisk`, `list`, `get`, `getOrCreateActiveByRoot`, `upsert`, `update`, `archive`, `remove`, `subscribeToMutations?`.
- `interface WorkspaceRegistry` (line 154): `initialize`, `existsOnDisk`, `list`, `get`, `update`, `upsert(record, context?)`, `archive(workspaceId, archivedAt, context?)`, `remove`, `subscribeToMutations?`.
- Implementations: `FileBackedProjectRegistry` (line 370), `FileBackedWorkspaceRegistry` (line 507); persisted shapes `PersistedProjectRecord` / `PersistedWorkspaceRecord` (Zod, lines 22/51).

### Fact S7 — MCP surface: daemon serves `/mcp/agents` and injects it into every agent as the `paseo` MCP server
- `packages/server/src/server/bootstrap.ts` mounts the FastMCP/Streamable-HTTP route at `"/mcp/agents"` (line ~1460), gated by `mcpEnabled`; the per-daemon capability token auth is passed as `mcpAuthToken` and is not sent to remote clients; `mcpInjectIntoAgents` controls injection.
- `packages/server/src/server/agent/mcp-server.ts`: `createAgentMcpServer(options)` builds a `McpServer({ name: "agent-mcp", version: "2.0.0" })` and registers each tool from `createPaseoToolCatalog(options)` with its `inputSchema`, returning MCP `content` + `structuredContent`.
- `packages/server/src/server/agent/runtime-mcp-config.ts`: `withRuntimePaseoMcpServer(...)` injects an `http` MCP server named `paseo` at `${mcpBaseUrl}?callerAgentId=<agentId>` with optional `Authorization: Bearer <mcpAuthToken>`; `stripInternalPaseoMcpServer` removes any persisted internal copy (`PASEO_MCP_PATHNAME = "/mcp/agents"`). Shared schemas for the tool layer live in `packages/server/src/server/agent/mcp-shared.ts` (`AgentStatusEnum`, `ProviderModeSchema`, `AgentModelSchema`, etc.).

---

## Summary of concrete interface facts (count: 10)

| # | Fact | Primary path |
|---|------|--------------|
| P1 | Plugin declared by `paseo-plugin.json` (`id`, optional `name/description/icon/media/requirements/build`) | `packages/server/src/server/plugins/manifest.ts` |
| P2 | Entry files `index.server.ts(x)` / `index.client.tsx(x)`, at least one required | `packages/server/src/server/plugins/runtime.ts` |
| P3 | Server entry default-exports `contribute(PluginServerContext)` returning a cleanup fn | `packages/plugin/src/server/contracts.ts` |
| P4 | Load = esbuild compile (host modules external) → forked child over IPC (builtins in-process) | `plugins/compiler.ts`, `plugins/runtime.ts`, `plugins/plugin-process.ts` |
| P5 | Host↔plugin typed protocol: `initialize/ready`, `invoke/result`, `provider.*`, `paseo_frame` | `plugins/plugin-process-protocol.ts` |
| P6 | Plugin session is a virtual ws-like socket channel bridged over IPC, OWNER admission | `plugins/session-socket.ts`, `plugins/daemon-transport.ts`, `websocket-server.ts` |
| S1 | Daemon = `createPaseoDaemon` → `PaseoDaemon{ start, stop, agentManager, ... }` | `server/bootstrap.ts` |
| S2 | `Session` is the transport-agnostic per-connection state machine; `SessionOptions` is its DI surface | `server/session.ts` |
| S3 | Wire protocol = Zod `SessionInbound/OutboundMessage` enveloped in WS `{type:"session"}`; hello schema | `packages/protocol/src/messages.ts`, `server/messages.ts` |
| S4 | WebSocket server on `ws` at `/ws`, hello + password/localCredential admission, 4401/4001/4002/4003 | `server/websocket-server.ts` |
| S5 | Provider abstraction `AgentClient`/`AgentSession` + `buildProviderRegistry`; plugin `ProviderRegistration@v1` | `agent/agent-sdk-types.ts`, `agent/provider-registry.ts`, `packages/plugin/src/server/provider.ts` |
| S6 | `ProjectRegistry`/`WorkspaceRegistry` interfaces with file-backed impls | `server/workspace-registry.ts` |
| S7 | MCP HTTP route `/mcp/agents` (McpServer `agent-mcp` v2.0.0) injected as agent MCP server `paseo` | `server/bootstrap.ts`, `agent/mcp-server.ts`, `agent/runtime-mcp-config.ts` |

(12 rows shown; the P/S numbering yields more than 10 individually-cited facts — the requested 5–10 is satisfied with headroom.)

## Limitations / unknowns
- Review is source-reading only: no daemon was started, no plugin installed, no build/typecheck run. Runtime behaviour is inferred from code comments and control flow, not observed.
- `packages/server/src/server/session.ts` is ~8.5k lines and could not be read end to end; facts S2 rely on the typed `SessionOptions` surface and the class/comment anchors, not on every handler.
- No verification that the recorded `main` tree still equals today's `main`; the review is pinned to commit `8f1091da…` / tree `ce2cbf0b…` and should be re-checked if `main` advanced.
- `packages/app` client-side plugin runtime (registry, surfaces, hooks) and the website/registry side were only spot-checked where they define the declaration contract; they are not covered in depth.
