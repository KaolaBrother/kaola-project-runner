# Issue #79 — Upstream primary-source facts: `william0wang/zcode-acp`

Scope: what upstream ACTUALLY documents/implements for ZCode desktop 3.12+ (`zcode app-server
--stdio`) compatibility, releases v0.42.2 – v0.42.5. Read-only web fetch; nothing cloned, installed,
or executed. Every claim below is a verbatim quote with its URL. Anything not quotable is listed
under UNKNOWNS / NOT DOCUMENTED.

## Retrieval log (all retrieved 2026-09-18)

| Source | URL | Retrieved |
| --- | --- | --- |
| CHANGELOG.md | https://raw.githubusercontent.com/william0wang/zcode-acp/main/CHANGELOG.md | 2026-09-18 |
| Releases API | https://api.github.com/repos/william0wang/zcode-acp/releases | 2026-09-18 |
| docs/ listing | https://api.github.com/repos/william0wang/zcode-acp/contents/docs | 2026-09-18 |
| docs/TROUBLESHOOTING.md | https://raw.githubusercontent.com/william0wang/zcode-acp/main/docs/TROUBLESHOOTING.md | 2026-09-18 |
| docs/PROTOCOL.md | https://raw.githubusercontent.com/william0wang/zcode-acp/main/docs/PROTOCOL.md | 2026-09-18 |
| src/backend/resolve.ts | https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/backend/resolve.ts | 2026-09-18 |
| src/backend/client.ts | https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/backend/client.ts | 2026-09-18 |
| src/server.ts | https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/server.ts | 2026-09-18 |
| src/config/runtime-model.ts | https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/config/runtime-model.ts | 2026-09-18 |
| src/config/account-provider.ts | https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/config/account-provider.ts | 2026-09-18 |
| src/handlers/server-requests.ts | https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/handlers/server-requests.ts | 2026-09-18 |
| src/handlers/session.ts | https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/handlers/session.ts | 2026-09-18 |
| docs/adr/ listing | https://api.github.com/repos/william0wang/zcode-acp/contents/docs/adr | 2026-09-18 |

Method caveat (honesty note): raw files were fetched through a summarizing fetch tool. Every block
below was requested as "copy character-for-character, no paraphrase", and the two load-bearing
blocks (`builtinProviderEnv`, the setModel fallback) were fetched TWICE in independently worded
requests and matched. Two requests for "every line containing X" returned a non-matching line once
(see UNKNOWNS), so line-level exhaustiveness claims are marked as unverified rather than asserted.

### Release/tag anchor (CHANGELOG.md, verbatim)

```
## [0.42.5](https://github.com/william0wang/zcode-acp/compare/v0.42.4...v0.42.5) (2026-09-17)

### Bug Fixes

* answer provider runtime headers with the coding-plan API key so GLM turns run ([ce3bdec](https://github.com/william0wang/zcode-acp/commit/ce3bdec14cd9f17090ca46a8ca00d235e2e144ce))

## [0.42.4](https://github.com/william0wang/zcode-acp/compare/v0.42.3...v0.42.4) (2026-09-17)

### Bug Fixes

* "inject both provider-config env vars so the 3.12+ CLI uses the bundled table verbatim" ([b0ecb89](https://github.com/william0wang/zcode-acp/commit/b0ecb8926860c1ee70a0f6f14aa1d2fc020f346f)), closes [#202](https://github.com/william0wang/zcode-acp/issues/202)

## [0.42.3](https://github.com/william0wang/zcode-acp/compare/v0.42.2...v0.42.3) (2026-09-17)

### Bug Fixes

* push the account provider snapshot and use the 3.12+ setModel shape so coding-plan models switch ([80ad523](https://github.com/william0wang/zcode-acp/commit/80ad523d42bea857bf920f9c4fe223b17f653b57))

## [0.42.2](https://github.com/william0wang/zcode-acp/compare/v0.42.1...v0.42.2) (2026-09-17)

### Bug Fixes

* inject ZCODE_BUILTIN_PROVIDER_CONFIG_FILE for bundled CLI launches ([8293b7c](https://github.com/william0wang/zcode-acp/commit/8293b7c4c3c8210e779a4f894018a8c5760010b6))
* require sustained probe failure before pruning a hub instance ([ea918c5](https://github.com/william0wang/zcode-acp/commit/ea918c51fa50eef641f8191f828abb9e72aeb0eb))
```

Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/CHANGELOG.md (retrieved
2026-09-18). Later releases exist and are relevant: `0.43.2` (2026-09-18) — `* derive the
account-to-config provider id mapping without the bundled table`.

---

## Q1 — Bundled provider config env vars, values, and path resolution

TWO env vars, both required. Verbatim from `src/backend/resolve.ts`:

```typescript
const PROVIDER_CONFIG_NAME = "zcode-builtin.json";
export const BUILTIN_PROVIDER_ENV = "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE";
export const PERSONAL_PROVIDER_ENV = "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE";

/**
 * Env vars pointing the CLI at its provider tables, mirroring the desktop
 * host's own injection. Locates the builtin file next to the resolved CLI
 * entry (sibling `provider/` — npm/dev layout — or `../config/provider/` —
 * the .app bundle layout) and returns BOTH
 * `{ZCODE_BUILTIN_PROVIDER_CONFIG_FILE, ZCODE_PERSONAL_PROVIDER_CONFIG_FILE}`;
 * `{}` when the entry is not a JS file, is missing, or carries no provider
 * config anywhere (old CLIs, PATH installs) — those boot without one.
 *
 * BOTH vars are required: the CLI's provider bootstrap uses the injected
 * builtin path VERBATIM only when the personal var is set too — with the
 * builtin alone it re-syncs the table into a version-keyed runtime copy
 * (`~/.zcode/v2/runtime/provider/<plat>/<version>/<endpoint dir>/zcode-builtin.json`)
 * and rewires
 * its configRevision to THAT copy's path. The account-config push's
 * `basedOnZcodeBuiltinRevision` hashes the injected path, so any rewire
 * silently voids the push and every account model answers "Provider
 * Registry 中不存在 Model" (observed 2026-09: one terminal env took the
 * re-sync path deterministically while another never did). The personal
 * value is the CLI's own default location, just made explicit to unlock the
 * verbatim branch.
 *
 * The derived value deliberately OVERRIDES any inherited ambient env: the
 * host injects version-keyed runtime paths
 * (`…/runtime/provider/<plat>/<appVersion>/endpoint-<hash>/zcode-builtin.json`)
 * that go stale or vanish across app updates, while the derived path always
 * matches the entry about to be launched. Only a {} result (no adjacent
 * config) leaves the ambient value untouched — for a non-bundled CLI that
 * ambient value is the best hint.
 */
export function builtinProviderEnv(entryArg?: string): NodeJS.ProcessEnv {
  const entry = entryArg ?? process.env.ZCODE_BIN ?? discoverZcodeBin();
  if (!entry || !/\.(cjs|mjs|js)$/.test(entry)) return {};
  const abs = path.resolve(entry);
  if (!existsSync(abs)) return {};
  const dir = path.dirname(abs);
  const candidates = [
    path.join(dir, "provider", PROVIDER_CONFIG_NAME),
    path.join(dir, "..", "config", "provider", PROVIDER_CONFIG_NAME),
  ];
  const found = candidates.find((c) => existsSync(c));
  if (!found) return {};
  const personal = path.join(os.homedir(), ".zcode", "v2", "provider_config.json");
  return existsSync(personal)
    ? { [BUILTIN_PROVIDER_ENV]: found, [PERSONAL_PROVIDER_ENV]: personal }
    : { [BUILTIN_PROVIDER_ENV]: found };
}
```

Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/backend/resolve.ts
(retrieved 2026-09-18; identical text returned on two independently worded fetches).

Anchor = the resolved CLI **entry script** (`ZCODE_BIN` or `discoverZcodeBin()`), not the `.app`
bundle root and not a hardcoded `/Applications` path. Only two candidates are probed, relative to
`dirname(entry)`: `provider/zcode-builtin.json` and `../config/provider/zcode-builtin.json`. The
personal value is always the fixed `~/.zcode/v2/provider_config.json`.

Note an internal tension worth recording (both quoted above, not inferred): the doc comment says
"BOTH vars are required", but the code returns builtin-only when `~/.zcode/v2/provider_config.json`
does not exist on disk.

argv and env assembly, verbatim:

```typescript
export function backendArgs(): string[] {
  const disallowed = disallowedToolsValue();
  return ["app-server", "--stdio", ...(disallowed ? ["--disallowed-tools", disallowed] : [])];
}
```
Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/backend/resolve.ts

```typescript
ensureBackend(): ZcodeBackend {
  if (this.backend && !this.backend.isDead) return this.backend;
  // builtinProviderEnv injects the CLI's built-in provider table the way the
  // desktop host does — a bare .app-bundle CLI cannot find it on its own.
  const env = { ...mergeEnvWithCreds(loadZcodeCredentials()), ...builtinProviderEnv() };
  let argv = resolveZcodeCommand();
  this.backendSandboxed = sandboxActive(this.sandboxRoots());
  if (this.backendSandboxed) {
```
Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/server.ts

Spawn, verbatim (`src/backend/client.ts`):

```javascript
this.proc = spawn(argv[0]!, argv.slice(1), {
  stdio: ["pipe", "pipe", "ignore"],
  env,
  detached: true,
});
```
Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/backend/client.ts

Corroborating symptom text (TROUBLESHOOTING.md, "Backend fails to start", step 4, verbatim):

> 4. Desktop-app CLI (3.12.3+) exits instantly with
>    `无法定位 CLI ZCode Built-in Provider Config`: the bundled CLI expects the
>    host to pass its provider table via `ZCODE_BUILTIN_PROVIDER_CONFIG_FILE`
>    (the desktop app does exactly that); launched bare, its own file lookup
>    cannot find the copy the bundle ships at `Resources/config/provider/`.
>    The bridge injects BOTH provider-table env vars automatically (see
>    `builtinProviderEnv` in `src/backend/resolve.ts`), deriving the builtin
>    path from the CLI it launches — the CLI uses an injected path verbatim
>    only when `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE` is set alongside it (it
>    defaults to `~/.zcode/v2/provider_config.json`); with the builtin var
>    alone the CLI re-syncs the table into a version-keyed runtime copy, which
>    voids the bridge's account-config push (next section). The derived value
>    also overrides an inherited ambient copy, which is version-keyed and goes
>    stale across app updates. To force a custom table, point `ZCODE_BIN` at a
>    CLI whose directory carries no adjacent `zcode-builtin.json` and export
>    the env var yourself.

Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/docs/TROUBLESHOOTING.md

**What this means for a Python reimplementation:** derive the builtin path from `dirname(zcode entry
script)` with exactly those two candidates, always also set `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE`
(`~/.zcode/v2/provider_config.json`), and let both override inherited ambient values.

---

## Q2 — Model shape / provider snapshot in 3.12+

### (a) The 3.12+ setModel shape and the legacy `runtimeModel` shape

Verbatim `applyModelSwitch` from `src/config/runtime-model.ts`:

```typescript
export async function applyModelSwitch(
  server: ZcodeAcpServer,
  zcodeSid: string,
  value: string,
): Promise<boolean> {
  const { providerId, modelId } = parseModelValue(value);
  const backend = server.ensureBackend();
  const registryProviderId = accountProviderIdFor(providerId);
  const model: Record<string, unknown> = { providerId: registryProviderId, modelId };
  // The object form requires the level for level-bearing models; resolve the
  // target's authoritative default from the captured create snapshot.
  const level = resolveDefaultReasoningLevel(server, zcodeSid, registryProviderId, modelId);
  if (level) model.options = { reasoningLevel: level };
  // 3.12+ shape first: `{sessionId, model:{providerId, modelId, options?},
  // persistAsWorkspaceLastUsed}`. `session/setModel` is strict in every build
  // we know, so an OLDER app-server answers `Unrecognized key: "options"` (it
  // predates `options`) or rejects a level-bearing model for the missing
  // overlay. Both are schema drift, not a bad target — fall back to the legacy
  // shape once (bare model ref + the `runtimeModel` provider overlay) so the
  // same bridge works against either build.
  const modern = await backend.request(
    server.nextId(),
    "session/setModel",
    { sessionId: zcodeSid, model, persistAsWorkspaceLastUsed: false },
    15000,
  );
  if (!modern.error) {
    invalidateModelCache(server, zcodeSid);
    return true;
  }
  const runtimeModel = buildRuntimeModel({ providerId, providerName: providerId, modelId });
  if (runtimeModel !== null) {
    const legacy = await backend.request(
      server.nextId(),
      "session/setModel",
      {
        sessionId: zcodeSid,
        model: { providerId, modelId },
        runtimeModel,
        persistAsWorkspaceLastUsed: false,
      },
      15000,
    );
    if (!legacy.error) {
      log(`runtime-model: switched via the legacy runtimeModel shape (${registryProviderId})`);
      invalidateModelCache(server, zcodeSid);
      return true;
    }
    warn(
      `runtime-model: switch failed (modern: ${modern.error.message}; legacy: ${legacy.error.message})`,
    );
    return false;
  }
  warn(`runtime-model: switch failed: ${modern.error.message}`);
  return false;
}
```

Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/config/runtime-model.ts
(retrieved 2026-09-18; the modern/legacy request pair matched across two independently worded
fetches).

The legacy overlay builder, verbatim (same file):

```typescript
export function buildRuntimeModel(ref: ModelRef, revision = "bridge"): unknown | null {
  const p = findProviderConfig(ref.providerId);
  if (!p) {
    log(`runtime-model: provider "${ref.providerId}" not in config.json`);
    return null;
  }
  const baseURL = p.options?.baseURL ?? DEFAULT_BASE_URL;
  // Model elements must carry the full definition (reasoning variants /
  // contextWindow / label) — a bare {modelId} overlay makes the backend fall
  // back to the apiFormat's default 2-state thought levels (enabled/disabled),
  // silently resetting the session's max/high/low dropdown on resume/switch.
  const models = Object.entries(p.models ?? {}).map(([modelId, m]) =>
    buildModelElement(modelId, (m ?? {}) as ModelEntry),
  );
  if (models.length === 0) models.push({ modelId: ref.modelId });
  const provider: Record<string, unknown> = {
    providerId: ref.providerId,
    kind: p.kind ?? DEFAULT_KIND,
    apiFormat: apiFormatForKind(p.kind),
    baseURL,
    models,
  };
  // Third-party providers must inline their apiKey — the backend won't resolve
  // it from anywhere else and the call fails with 401 without it. Builtin
  // providers use OAuth/config auth and must NOT send an inline key.
  if (!isBuiltinProvider(ref.providerId) && p.options?.apiKey) {
    provider.apiKey = { source: "inline", value: p.options.apiKey };
  }
  return {
    revision,
    generatedAt: Date.now(),
    model: { providerId: ref.providerId, modelId: ref.modelId },
    provider,
  };
}
```

### (b) `session/create` params as quoted from `src/handlers/session.ts`

```javascript
const createParams: Record<string, unknown> = {
  workspace: workspaceFor(pending.cwd),
  mode: process.env.ZCODE_ACP_MODE || "yolo",
};
if (pending.mcpServers && pending.mcpServers.length > 0) {
  createParams.mcpServers = pending.mcpServers;
  log(`session/create carrying ${pending.mcpServers.length} client MCP server(s)`);
} else {
  const remembered = server.sessionMcpServers.get(acpSid);
  if (remembered) {
    createParams.mcpServers = remembered;
    log(`session/create carrying ${remembered.length} remembered client MCP server(s)`);
  }
}
```
Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/handlers/session.ts
No `model` and no `runtimeModel` key appears in the quoted block. Whether a later statement in the
same function adds one is NOT VERIFIED (see UNKNOWNS).

### (c) The provider snapshot that entitles the 3.12+ registry

Verbatim `src/config/account-provider.ts`:

```typescript
/**
 * Build the account snapshot: every coding-plan provider the bundled table
 * declares, with entitlement taken from config.json's enabled builtin plans.
 * Returns null when there is nothing to push (no table, no zhipu providers).
 */
export function buildAccountProviderConfig(): AccountProviderPayload | null {
  const found = readBuiltinTable();
  if (!found) return null;
  const rules =
    found.table.config?.providerConfigRules?.providerRules?.filter(
      (r) => r.config?.access?.type === "zhipu-account",
    ) ?? [];
  if (rules.length === 0) return null;
  const enabled = entitledBuiltinProviders();
  const providers: AccountProviderPayload["providers"] = {};
  const states: AccountProviderPayload["states"] = {};
  for (const rule of rules) {
    const entitled = enabled.has(configProviderIdFor(rule.providerId));
    providers[rule.providerId] = {
      builtinModelIds: rule.config?.builtinModelIds,
      access: { type: "zhipu-account", entitled },
    };
    states[rule.providerId] = {
      availability: entitled ? "available" : "unavailable",
      entitled,
      current: entitled,
    };
  }
  return {
    revision: `account:bridge:${Date.now()}`,
    basedOnZCodeBuiltinRevision: builtinRevision(found.file, found.table.revision),
    providers,
    states,
  };
}
```

```typescript
function builtinRevision(file: string, revision: number | undefined): string {
  const hash = createHash("sha256").update(path.resolve(file)).digest("hex");
  return `zcode-builtin:${revision ?? 0}:${hash}`;
}
```

```typescript
export async function pushAccountProviderConfig(
  backend: ZcodeBackend,
  nextId: () => number,
): Promise<boolean> {
  const payload = buildAccountProviderConfig();
  if (!payload) return false;
  try {
    const resp = await backend.request(
      nextId(),
      "provider/updateAccountConfig",
      payload as unknown as Record<string, unknown>,
      10000,
    );
    if (resp.error) {
      if (resp.error.code === -32601) {
        log("account-provider: backend has no provider/updateAccountConfig (old CLI) — skipped");
      } else {
        warn(`account-provider: push failed: ${resp.error.message}`);
      }
      return false;
    }
```
Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/config/account-provider.ts

Call site (verbatim, `src/handlers/session.ts`, inside `syncProviderRegistry`):

```typescript
/**
 * Push the provider registry to the backend so third-party providers (those in
 * config.json) are recognised. The V4 backend doesn't auto-load them from
 * config.json — without this RPC a session switching to a third-party model
 * fails with `provider_not_configured`. Best-effort: failures are logged, not
 * thrown, so a registry push problem never blocks session creation.
 */
async function syncProviderRegistry(server: ZcodeAcpServer, cwd: string): Promise<void> {
  try {
    // Account-plan providers first: 3.12+ app-servers build their registry from
    // the bundled table + personal config + an ACCOUNT snapshot the desktop
    // host pushes (`provider/updateAccountConfig`). Headless launches have no
    // host, so every `account:*` provider stays entitled:false and the GLM
    // models the user's config selects never reach `settings.model.available`
    // (verified 2026-09 — switches then fail with "Provider Registry 中不存在
    // Model"). Pushing the snapshot restores desktop parity. Best-effort.
    await pushAccountProviderConfig(server.ensureBackend(), () => server.nextId());
```
Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/handlers/session.ts

**What this means for a Python reimplementation:** model selection is a separate
`session/setModel` with `{sessionId, model:{providerId, modelId, options?{reasoningLevel}},
persistAsWorkspaceLastUsed}`; `runtimeModel` is only a legacy fallback payload; and a
`provider/updateAccountConfig` snapshot (whose `basedOnZCodeBuiltinRevision` is
`zcode-builtin:<revision>:<sha256 of the resolved builtin table PATH>`) must be pushed before
`account:*` models are selectable.

---

## Q3 — `interaction/requestProviderRuntimeHeaders`

Direction: server -> client (the app-server asks the bridge). Handled in the bridge's
server-request handler. Verbatim `src/handlers/server-requests.ts`:

```javascript
if (isProviderRuntimeHeadersRequest(method)) {
  const sel = (params as { modelSelection?: { providerId?: string }; providerId?: string })
    .modelSelection?.providerId;
  const requestAuth = codingPlanRequestAuthFor(
    sel ?? (params as { providerId?: string }).providerId,
  );
  if (requestAuth) {
    log("  provider runtime headers: serving the coding-plan API key (config.json)");
    sendZcodeReply(backend, zcodeReqId, { headersApplied: true, requestAuth });
    return;
  }
  warn(
    "  ⚠ provider runtime headers requested (Start Plan captcha session); " +
    "the headless bridge cannot provide it — declining",
  );
  sendZcodeReply(backend, zcodeReqId, {
    headersApplied: false,
    errorMessage: PROVIDER_RUNTIME_HEADERS_UNAVAILABLE,
  });
  return;
}
```

```typescript
function isProviderRuntimeHeadersRequest(method: string): boolean {
  return method === "interaction/requestProviderRuntimeHeaders";
}
```

```typescript
const PROVIDER_RUNTIME_HEADERS_UNAVAILABLE =
  "Start Plan providers require an Aliyun captcha session that only the " +
  "ZCode desktop app can provide. Use a GLM Coding Plan provider for " +
  "headless/editor sessions (see docs/TROUBLESHOOTING.md).";
```
Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/handlers/server-requests.ts

The API-key answer builder, verbatim (`src/config/account-provider.ts`):

```typescript
export function codingPlanRequestAuthFor(
  accountProviderId: string | undefined,
): { apiKey: string } | null {
  if (!accountProviderId?.startsWith("account:")) return null;
  const rule = readBuiltinTable()?.table.config?.providerConfigRules?.providerRules?.find(
    (r) => r.providerId === accountProviderId,
  );
  if (rule?.config?.access?.mode !== "individual-coding-plan") return null;
  const legacyId = configProviderIdFor(accountProviderId);
  if (legacyId === accountProviderId) return null;
  if (!entitledBuiltinProviders().has(legacyId)) return null;
  try {
    const cfg = JSON.parse(readFileSync(ZCODE_CREDS_PATH, "utf8")) as {
      provider?: Record<string, { enabled?: boolean; options?: { apiKey?: string } }>;
    };
    const apiKey = cfg.provider?.[legacyId]?.options?.apiKey?.trim();
    return apiKey ? { apiKey } : null;
  } catch {
    return null;
  }
}
```

Timing — verbatim from TROUBLESHOOTING.md:

> **Why:** the 3.12+ backend asks its host for provider runtime headers
> (`interaction/requestProviderRuntimeHeaders`) before EVERY model request on an
> account provider. A `headersApplied:false` answer makes the turn fail with
> -32031 and retry.

And, for the Start Plan case:

> before each model request the backend asks its host via
> `interaction/requestProviderRuntimeHeaders` to solve an Aliyun captcha and
> inject `X-Aliyun-Captcha-Verify-Param`/`-Region` headers.

Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/docs/TROUBLESHOOTING.md

So: per MODEL REQUEST (not per session, and not merely per user prompt — a turn with tool calls
makes several model requests).

Credential handling (no key material reproduced here): the key is read from `ZCODE_CREDS_PATH`
(documented as `~/.zcode/v2/config.json`) at `provider[<legacy builtin id>].options.apiKey`, trimmed,
returned as `{ apiKey }` inside `requestAuth`, and the log line deliberately records only that a key
was served, never its value. `buildRuntimeModel` likewise inlines a third-party key only as
`{ source: "inline", value: ... }` and explicitly must NOT do so for builtin providers.

**What this means for a Python reimplementation:** the bridge MUST implement an inbound
server->client request handler for `interaction/requestProviderRuntimeHeaders` and answer
`{headersApplied: true, requestAuth: {apiKey: "..."}}` for coding-plan providers, otherwise every
GLM turn fails with -32031 and retries forever.

---

## Q4 — Version gating: detect-and-support-both, keyed on ERROR, not on a version string

No version string or `initialize` capability check was found. `src/backend/client.ts` returned
"**NO VERSION DETECTION** exists in this file. There is no code that reads version strings, checks
initialize results for capabilities, or compares version numbers."
(https://raw.githubusercontent.com/william0wang/zcode-acp/main/src/backend/client.ts)

The two gating mechanisms that ARE quotable are both error-driven:

1. Model switching — try modern, fall back once on ANY error (quoted in full under Q2a):
   > `// 3.12+ shape first: ... Both are schema drift, not a bad target — fall back to the legacy`
   > `// shape once (bare model ref + the `runtimeModel` provider overlay) so the`
   > `// same bridge works against either build.`
2. Provider snapshot — treat JSON-RPC -32601 as "old CLI" and skip silently:
   > `if (resp.error.code === -32601) {`
   > `  log("account-provider: backend has no provider/updateAccountConfig (old CLI) — skipped");`

Version FLOORS appear only as human-readable troubleshooting text (`Must be >= 0.14.8`;
`Desktop-app CLI (3.12.3+)`), not as runtime gates.

**What this means for a Python reimplementation:** do not gate on a version probe. Send the modern
shape, inspect the JSON-RPC error, and fall back once; treat -32601 on
`provider/updateAccountConfig` as a benign old-CLI no-op.

---

## Q5 — TROUBLESHOOTING.md coverage of the two Issue-#79 symptoms

Direct answer, from an explicit presence check on the raw file (retrieved 2026-09-18,
https://raw.githubusercontent.com/william0wang/zcode-acp/main/docs/TROUBLESHOOTING.md):

- `"Select a model"` / `"Select a model before continuing"` — **NOT DOCUMENTED** (string absent).
- `"-32602"` — **NOT DOCUMENTED** (string absent).
- `"Unrecognized key"` — **NOT DOCUMENTED** in TROUBLESHOOTING.md. The phrase appears only in
  `src/config/runtime-model.ts` as `Unrecognized key: "options"` describing the OLDER app-server
  rejecting the new shape — i.e. the inverse direction of the Issue-#79 report.

What IS documented are the two behavioural symptoms, quoted verbatim:

> ### Switching to a GLM coding-plan model fails / snaps back to a third-party model
>
> **Symptom:** picking GLM-5.3 (or GLM-5.3-Flash) in the model picker errors out or the UI
> immediately falls back to a third-party model (e.g. DeepSeek); third-party models switch
> fine. The bridge log (`ZCODE_ACP_DEBUG=1`) shows
> `runtime-model: switch failed (modern: Provider Registry 中不存在 Model …)`.
>
> **Why:** on 3.12+ the backend registry is entitled by an account snapshot the bridge
> pushes (`provider/updateAccountConfig`). The push carries a `basedOnZCodeBuiltinRevision`
> hash of the provider-table PATH the backend resolved; if the backend resolved a different
> copy (its version-keyed runtime copy under
> `~/.zcode/v2/runtime/provider/<plat>/<version>/…` instead of the injected
> `Resources/config/provider/` path), it accepts the push but silently ignores it — every
> `account:*` model is then "not in the Provider Registry". The CLI only uses an injected
> builtin path verbatim when BOTH `ZCODE_BUILTIN_PROVIDER_CONFIG_FILE` and
> `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE` are set; `builtinProviderEnv` injects both.
>
> **Troubleshooting steps:**
>
> 1. Check which table the backend resolved:
>
>    ```bash
>    grep -a provider_registry.ready ~/.zcode/cli/log/zcode-$(date +%F).jsonl | tail -1
>    ```
>
>    The `configRevision` hash must match the injected path. Verify with:
>
>    ```bash
>    python3 -c "import hashlib,os;print(hashlib.sha256(b'/Applications/ZCode.app/Contents/Resources/config/provider/zcode-builtin.json').hexdigest()[:16])"
>    ```
>
> 2. If the hashes differ, the bridge is older than the dual-env fix (0.42.4+) or
>    `ZCODE_BIN` points at a CLI without an adjacent `zcode-builtin.json` — check
>    `echo $ZCODE_BIN` in the launching shell.
>
> 3. Note `session.model_selection.persist_failed` ("FOREIGN KEY constraint failed")
>    appears on EVERY switch — including working ones — and is a backend persistence
>    wart, not the switching bug. The success signal is the following
>    `session.model.updated` event in the same log.

> ### Switching to a GLM model works but every send fails / retries forever
>
> **Symptom:** the model picker shows the GLM model after switching, but sending a
> message errors immediately and retries; the backend log shows
> `model.request.failed` with `reason:"unknown"` on `account:bigmodel-…` providers.
>
> **Why:** the 3.12+ backend asks its host for provider runtime headers
> (`interaction/requestProviderRuntimeHeaders`) before EVERY model request on an
> account provider. A `headersApplied:false` answer makes the turn fail with
> -32031 and retry. The bridge (0.42.5+) answers with the coding plan's API key
> from `~/.zcode/v2/config.json` (`codingPlanRequestAuthFor`) — if sends still
> fail, check that the enabled `builtin:bigmodel-coding-plan` entry carries a
> non-empty `options.apiKey` in that file. Start-plan providers stay declined
> (Aliyun captcha — desktop app only, issue #123).

Source: https://raw.githubusercontent.com/william0wang/zcode-acp/main/docs/TROUBLESHOOTING.md

**What this means for a Python reimplementation:** the two documented failure modes map 1:1 to the
two fixes (dual env injection + account snapshot; runtime-headers answer). The exact Issue-#79
strings are not upstream vocabulary, so do not search upstream for them.

---

## UNKNOWNS / NOT DOCUMENTED

1. **`-32602 "Unrecognized key: runtimeModel"` — NOT DOCUMENTED upstream.** The string does not
   appear in TROUBLESHOOTING.md. Upstream's quoted comment describes the opposite drift
   (`Unrecognized key: "options"` from an OLDER app-server). Upstream's fallback still SENDS
   `runtimeModel` as its legacy retry, so upstream does not treat `runtimeModel` as universally
   rejected by 3.12+.
2. **"Select a model before continuing" — NOT DOCUMENTED** anywhere in TROUBLESHOOTING.md.
3. **docs/PROTOCOL.md does not cover any of this.** A targeted read found no mention of
   `runtimeModel`, `session/setModel`, provider snapshot, `interaction/requestProviderRuntimeHeaders`,
   `3.12`, or `app-server --stdio`; its only model reference is
   `"model": { "current": { "modelId": "GLM-5.2" } }` in a `session/read` example.
   (https://raw.githubusercontent.com/william0wang/zcode-acp/main/docs/PROTOCOL.md, 2026-09-18)
4. **The ZCode-side schema for `interaction/requestProviderRuntimeHeaders` is NOT DOCUMENTED.** Only
   the bridge's defensive destructuring is evidence: it reads `params.modelSelection.providerId`
   with `params.providerId` as a fallback. Whether other params exist, and the authoritative response
   schema (beyond `headersApplied`, `requestAuth`, `errorMessage`), is unknown. In particular whether
   a `headers` map key is accepted alongside `requestAuth` is NOT DOCUMENTED — the Aliyun header
   names `X-Aliyun-Captcha-Verify-Param`/`-Region` are mentioned only in prose.
5. **Exhaustive `session/create` params NOT VERIFIED.** The quoted `createParams` block carries
   `workspace`, `mode`, and optional `mcpServers` only. Whether a `model`/`runtimeModel` key is added
   later in the same function was not confirmed; one "every line containing session/create" query
   returned a non-matching line, so that tool answer was discarded rather than relied on.
6. **`accountProviderIdFor` / `configProviderIdFor` mapping rules NOT QUOTED.** Note CHANGELOG 0.43.2
   (2026-09-18): `* derive the account-to-config provider id mapping without the bundled table` — the
   mapping changed after 0.42.5, so any reimplementation copying 0.42.x id mapping is already behind.
7. **`readBuiltinTable`, `entitledBuiltinProviders`, `ZCODE_CREDS_PATH`, `discoverZcodeBin`,
   `resolveZcodeCommand`, `buildModelElement`, `resolveDefaultReasoningLevel` definitions NOT
   FETCHED.** Their behaviour is asserted only by the comments quoted above.
8. **The `AccountProviderPayload` TypeScript interface itself was not quoted** — the payload shape is
   evidenced by the constructor function only.
9. **No GitHub Release BODY text was retrieved verbatim**; the releases API answer paraphrased. The
   quoted CHANGELOG.md entries (release-please generated, same content) are the verbatim anchor.
10. **Casing inconsistency, unresolved:** the code emits `basedOnZCodeBuiltinRevision` (capital C)
    while the `builtinProviderEnv` doc comment writes `basedOnZcodeBuiltinRevision` (lowercase c).
    Which the backend requires is NOT DOCUMENTED; the emitted key is the safer choice.
11. **-32031** is quoted as the failure code for `headersApplied:false`, but its meaning is not
    defined in any upstream doc read here.
12. **No ADR covers 3.12+ compatibility** — docs/adr/ contains 0001–0007, none on provider config,
    model shape, or runtime headers.
