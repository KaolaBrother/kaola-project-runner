# Issue #79 — local ground truth (read-only, this Mac, 2026-09-18)

Method: passive inspection only. No ZCode/tmux session was started, attached to or killed.
No file outside this one was created or modified. `~/.zcode/v2/credentials.json`,
`setting.json` and `provider_config.json` were **never opened** (only `ls`/`stat`).
Every value that looks like key material is `<REDACTED>`.

Repo reading: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-79`
(plus read-only reads of `kaola-workflow/` on main and of `/tmp/kpr-i74-live-JM7IDB/checkout`).

---

## A. VERSIONS

| Fact | Value | How measured |
| --- | --- | --- |
| Desktop app short version | `3.12.3` | `plutil -p /Applications/ZCode.app/Contents/Info.plist` → `CFBundleShortVersionString` |
| Desktop app build | `3.12.3.7463` | same, `CFBundleVersion` |
| Bundle id | `dev.zcode.app` | same, `CFBundleIdentifier` |
| Bundled CLI version | `0.16.5` | `node /Applications/ZCode.app/Contents/Resources/glm/zcode.cjs --version` (exit 0, single line) |
| App install mtime | `Sep 16 23:06` | `ls -la /Applications/ZCode.app/Contents` |

`--version` is provably side-effect-free in this build: the provider-runtime bootstrap gate
short-circuits on it —
`function BSo(e){if(e.some(r=>r==="--help"||r==="-h"||r==="--version"||r==="-v"))return!1; ...}`
(`a(BSo,"requiresProviderRuntime")`).

**Version-string trap:** the CLI still reports `0.16.5`, the same string recorded as the working
baseline under desktop **3.11.2** (`kaola-workflow/archive/bundle-51/uat-live-2026-09-16.md:7,111`).
The CLI version string did **not** change while the protocol did. `acp_verified_versions:
"cli=0.16.5;..."` in `platforms/zcode.yaml` is therefore not a discriminator for this regression.

Node runtime: the archived `KAOLA_ZCODE_NODE=~/.local/node-v24.14.0-darwin-arm64/bin/node`
(bundle-62) **no longer exists on this Mac**. The only node now present is
`/opt/homebrew/bin/node` (also the value used in newer archived probes).

---

## B. ENTRY / BUNDLE LAYOUT — **the bundled provider config cannot be found from the entry**

### B.1 What the adapter points at

`scripts/adapters/zcode.sh` and `scripts/kaola-zcode-acp.py` take the entry/node only from
`--zcode-entry/--zcode-node` or `KAOLA_ZCODE_ENTRY/KAOLA_ZCODE_NODE` (no PATH search). The
concrete values used across the archive:

- `KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`
  (`archive/issue-65/evidence/probes/run-live-matrix.sh:6`, `archive/issue-70/evidence/live-2026-09-18.md:20`,
  `archive/issue-67/evidence/MEASURED.md:18`, `archive/issue-66/evidence/live-loop-2026-09-18.md:10`,
  `archive/bundle-62/mission-list.md:23`)
- `KAOLA_ZCODE_NODE=/opt/homebrew/bin/node` (current) or the now-missing
  `~/.local/node-v24.14.0-darwin-arm64/bin/node` (bundle-62)

Child spawn: `scripts/kaola-zcode-acp.py:449-450`
`subprocess.Popen([self.node, self.entry, "app-server", "--stdio"], ...)`.

### B.2 Real on-disk layout

```
/Applications/ZCode.app/Contents/Resources/
├── app.asar                       (307 MB, desktop UI)
├── config/
│   ├── default.json               (341 B, feedback/community URLs only)
│   └── provider/
│       └── zcode-builtin.json     (182137 B)   <-- THE BUNDLED PROVIDER CONFIG
├── glm/
│   ├── .node-bundle-meta.json     {"runtime":"electron-node","entry":"zcode.cjs",
│   │                               "platform":"darwin-arm64",
│   │                               "source":"apps/zcode-cli/packages/cli/dist/zcode.cjs"}
│   ├── packages/                  (8 plugins)
│   └── zcode.cjs                  (11416833 B)  <-- THE ENTRY
```

Note there is **no** `glm/provider/` directory.

### B.3 The env names (exact hits, `glm/zcode.cjs`)

Exactly two `*PROVIDER_CONFIG*` env names exist in the whole 11 MB bundle
(`grep -o "[A-Z][A-Z0-9_]*PROVIDER_CONFIG[A-Z0-9_]*"` → 1 hit each):

```js
var AR,CSe,x$,ESe,Mhr=I(()=>{"use strict";
  AR ="ZCODE_BUILTIN_PROVIDER_CONFIG_FILE",
  CSe="ZCODE_BUILTIN_PROVIDER_BUNDLED_CONFIG_FILE",
  x$ ="ZCODE_PERSONAL_PROVIDER_CONFIG_FILE",
  ESe="provider_config.json";
  a(Ohr,"resolveNodeProviderRuntimePaths")});
```

Consumer 1 — `resolveNodeProviderRuntimePaths` (both-or-neither):

```js
function Ohr(e){let t=e[AR]?.trim(),r=e[x$]?.trim();
  if(!t&&!r)return null;
  if(!t||!r)throw new Error("ZCode Built-in 与 Personal Provider Config 路径必须同时提供");
  return Object.freeze({zcodeBuiltinFilePath:t,personalFilePath:r})}
```

Consumer 2 — the process provider registry, `a(q3e,"startProcessProviderRegistryRuntime")`:

```js
async function q3e(e,t={}){let r=Ohr(e);
  if(!r)throw new Error("缺少进程 Provider Registry 的 ZCode Built-in / Personal Config 路径");
  let n=new y$, o=t.standalone?t.standalone.credentialStore??gb({env:{...e}}):void 0, ...
```

Consumer 3 — the CLI bootstrap, `a($hr,"prepareCliProviderRuntimeEnv")`, called from `main()`:

```js
async function HMs(){let e=process.argv.slice(2); ...
  e.includes("--prepare-storage")||Object.assign(process.env,await bnr());
  e.includes("--prepare-storage")||Object.assign(process.env,await $hr({argv:e,env:process.env}));
  let{run:s}=await ...
```

```js
async function $hr(e){ if(!BSo(e.argv))return{};
  let t=e.env[AR]?.trim(), r=e.env[x$]?.trim(),
      n=e.dataBaseDir??e.env.ZCODE_DATA_BASE_DIR?.trim()??homedir();
  if(t&&r)return{[AR]:t,[x$]:r};                       // <-- both set: pass through, no probing
  let o=t??await qSo({dataBaseDir:n,entrypoint:e.entrypoint??process.argv[1],sea:e.sea??VSo()}),
      i=r??join(n,".zcode","v2",ESe),                  // default personal = ~/.zcode/v2/provider_config.json
      s=e.appVersion??Zb, c=e.platform??xSe(), l=$p(e.env),
      u=wSe({environmentConfigRoot:join(n,".zcode","v2"),platform:c,appVersion:s,zcodeEndpointOrigin:l}),
      d=new Fy({bundledFilePath:o,activeFilePath:u.activeFilePath,watch:!1});
  try{await d.read()}finally{d.dispose()}
  return{[AR]:u.activeFilePath,[CSe]:o,[x$]:i}}
```

`BSo` (`requiresProviderRuntime`) returns **true** for `app-server`:

```js
function BSo(e){if(e.some(r=>r==="--help"||r==="-h"||r==="--version"||r==="-v"))return!1;
  if(e.some(r=>r==="--prompt"||r.startsWith("--prompt=")||r==="--target"||r.startsWith("--target=")))return!0;
  let t=e[0];return t===void 0||t.startsWith("-")?!0
    :t==="tui"||t==="app-server"||t==="agent-server"||t==="login"||t==="logout"}
```

**The fallback resolution when unset** — `a(qSo,"resolveBundledZCodeBuiltinProviderConfig")`:

```js
async function qSo(e){ if(e.sea?.isSea()){...getAsset("zcode-provider/zcode-builtin.json")...}
  let t=e.entrypoint?.trim();
  if(!t)throw new Error("无法定位 CLI ZCode Built-in Provider Config：缺少入口路径");
  let r=dirname(resolve(t)),
      n=[ join(r,"provider","zcode-builtin.json"),
          resolve(r,"../../../../../config/provider/zcode-builtin.json") ],
      o=n.find(i=>existsSync(i));
  if(o)return o;
  throw new Error(`无法定位 CLI ZCode Built-in Provider Config：${n.join(", ")}`)}
```

### B.4 Measured: both fallback candidates miss

```
$ node -e 'const p=require("path"),fs=require("fs");
  const r=p.dirname(p.resolve("/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs"));
  console.log(r);
  console.log(p.join(r,"provider","zcode-builtin.json"), fs.existsSync(...));
  console.log(p.resolve(r,"../../../../../config/provider/zcode-builtin.json"), fs.existsSync(...));'
entryDir: /Applications/ZCode.app/Contents/Resources/glm
cand1:    /Applications/ZCode.app/Contents/Resources/glm/provider/zcode-builtin.json  false
cand2:    /config/provider/zcode-builtin.json                                         false
actual bundled file exists: true   (/Applications/ZCode.app/Contents/Resources/config/provider/zcode-builtin.json)
```

The 5-level `../../../../../` is written for the **source tree** (`apps/zcode-cli/packages/cli/dist/zcode.cjs`
→ repo-root `config/provider/`, see `.node-bundle-meta.json.source`). In the **installed app**
the entry is only ONE level below `config/`, so five levels up resolves to `/` and the file is missed.
This is a packaging/derivation mismatch in ZCode 3.12.3, not a Runner bug — but the Runner is the
only caller that launches the entry without the desktop's own env.

Consequence: `main()` throws before `run()`, exitCode 1, child dies immediately.
Confirmed live, three independent probes (Issue #74, 2026-09-18):

```
$ cat kaola-workflow/issue-74/evidence/live/03b-appserver-probe.err   # and 03c, 03d — byte-identical
无法定位 CLI ZCode Built-in Provider Config：/Applications/ZCode.app/Contents/Resources/glm/provider/zcode-builtin.json, /config/provider/zcode-builtin.json
```

`scripts/kaola-zcode-acp.py` cannot repair this today: `ENV_ALLOWLIST` (lines 107-121) is
`HOME, PATH, TMPDIR, LANG, LC_ALL, LC_CTYPE, USER, LOGNAME, SHELL, TZ, TERM, KAOLA_ZCODE_ENTRY,
KAOLA_ZCODE_NODE` — neither provider-config env name is forwarded or set.

### B.5 Does the bundled provider config contain a secret? **No.**

`/Applications/ZCode.app/Contents/Resources/config/provider/zcode-builtin.json`:
`{"schemaVersion":1,"revision":28,"config":{"providerConfigRules":{"templateRules":[20],
"providerRules":[8]},"modelConfigRules":...}}`. It is a **rules/template catalog**, zero concrete
provider instances, zero `apiKey`/`token`/`secret`/`password` literal values (programmatic scan:
0 hits; the 20 `*Url` hits are `apiKeyManagementUrl` console URLs). Contains `zhipu-account` ×8 and
`individual-coding-plan` ×12.

The per-machine "active" copy derived from it —
`~/.zcode/v2/runtime/provider/darwin-aarch64/3.12.3/endpoint-78d7c3bef4024722642626fe3669a799/zcode-builtin.json`
(186432 B, mode 0600) — is the **same revision 28, same shape, also 0 secret literals**.
Path shape is produced by `a(wSe,"resolveZCodeBuiltinCachePaths")`:
`<root>/runtime/provider/<platform>/<appVersion>/endpoint-<sha256(origin)[0:32]>/zcode-builtin.json`
plus a sibling `zcode-builtin-refresh.json` control file. A stale `.../0.0.0-dev/...` sibling also exists.

`~/.zcode/v2/provider_config.json` (the `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE` default, 206 B, mode
0600) exists — confirmed by `ls` only, contents **not read**.

---

## C. `requestProviderRuntimeHeaders` + accepted model shape in the INSTALLED 3.12.3 build

### C.1 `runtimeModel` does not exist in this build

```
grep -c runtimeModel /Applications/ZCode.app/Contents/Resources/glm/zcode.cjs
0
```

Zero occurrences. The key the adapter sends is not merely rejected by a schema — the concept is gone.

### C.2 `session/create` accepted params (strict)

```js
hKe=m.object({sessionId:fe.optional(),workspace:Wi,parentSessionId:fe.optional(),
  mode:vw.optional(), model:mo.optional(), persistence:cKe.optional(),
  thoughtLevel:fe.optional(),titleGenerationEnabled:m.boolean().optional(),
  mcpServers:m.array(b3).optional(),toolAllowlist:m.array(fe).optional(),
  toolDenylist:m.array(fe).optional(),importedHistory:NKt.optional(),
  offPeakToolEnabled:m.boolean().optional()}).strict()
```

Handler: `async function E8n(e,t,r,n){let o=eo(hKe,t); ... let v=o.model; ...
await u.app.setModel(hme(v))...}` with `function hme(e){return `${e.providerId}/${e.modelId}`}`
(`a(hme,"formatProtocolModelSelection")`).

### C.3 `session/resume` accepted params (strict) — **no model at all**

```js
gKe=m.object({sessionId:fe,workspace:Wi.optional(),thoughtLevel:fe.optional(),
  mcpServers:m.array(b3).optional(),toolAllowlist:m.array(fe).optional(),
  toolDenylist:m.array(fe).optional(),offPeakToolEnabled:m.boolean().optional()}).strict()
```

### C.4 `session/setModel` accepted params (strict)

```js
OKe=m.object({sessionId:fe, model:mo,
  expectedRevision:m.number().int().nonnegative().optional(),
  persistAsWorkspaceLastUsed:m.boolean().default(!0)}).strict()
```

with the one and only model shape:

```js
mo=m.object({providerId:m.string().trim().min(1),modelId:m.string().trim().min(1),
  options:m.object({reasoningLevel:m.string().trim().min(1).optional()}).strict().optional()}).strict()
```

Handler `a(U8n,"setModel")`: `let r=eo(OKe,t); ... await n.app.setModel(r.model)`, and
`app.setModel` resolves **against the provider registry**:

```js
setModel:a(async(s,c)=>{let l=typeof s=="string"?kUn(e.providerRegistry,s,e.configuredDefaultModelSelection,
  {allowMissingReasoning:!0}):Y6(e.providerRegistry,s);
  if(!l)throw new Error(`Provider Registry 中不存在 Model: ${s}`); ...},"setModel")
```

So there is **no channel on `session/create` / `session/resume` / `session/setModel` to inject a
provider, baseURL or apiKey.** Only `{providerId, modelId, options?}`, and the pair must already be
in the registry.

### C.5 `-32602 "Unrecognized key"` is generic strict-schema rejection

```js
function SCs(e){let t=e?.issues; ... let r=t.slice(0,5).map(o=>`${...path.join(".")||"(root)"}: ${o.message??"invalid"}`) ...}
function eo(e,t){try{return e.parse(t)}catch(r){let n=SCs(r);
  throw new Cs(-32602,n?`Invalid params — ${n}`:"Invalid params",r)}}
```

zod v4 `unrecognized_keys` → `Unrecognized key: "runtimeModel"`, wrapped as
`-32602 Invalid params — (root): Unrecognized key: "runtimeModel"`. Matches the archived raw line
verbatim (see E.2).

### C.6 `"Select a model before continuing"` — exactly one site

```js
function Ym(e,t){ if(!t.selection)
    throw Ie(he.ConfigurationError,"Select a model before continuing",{recoverable:!0});
  return e.modelFactory({...t,selection:t.selection})}
...
a(Ym,"createRuntimeModel");
```

It fires inside **`createRuntimeModel`** when the session has no resolved model selection —
i.e. an empty/unusable provider registry, at turn phase `model_creation`. It is not a prompt-shape
error and not an auth error.

### C.7 The 3.12 replacement mechanism: `interaction/requestProviderRuntimeHeaders` (server → client)

Method table entry:
`interactionRequestProviderRuntimeHeaders:"interaction/requestProviderRuntimeHeaders"`.

Default port used by the app-server, `a(F3n,"createProviderRuntimeHeadersPort")`:

```js
function F3n(e,t){return{shouldRefreshBeforeModelRequest(){return!0},
 async refreshBeforeModelRequest(r){
  let n=`${r.sessionId}:provider-runtime-headers:${randomUUID()}`,o;
  try{ o=await e.requestClient(dr.interactionRequestProviderRuntimeHeaders,
        {requestId:n,sessionId:r.sessionId,turnId:r.turnId,workspace:t,
         modelSelection:{providerId:r.providerId,modelId:r.modelId},
         providerId:r.providerId,...r.accountAccess?{accountAccess:r.accountAccess}:{},
         reason:r.reason}, VKe,{signal:r.abortSignal,trace:...,timeoutMs:ICs})
  }catch(i){ ...z3n=-32022 captcha timeout path... }
  if(!o.headersApplied)throw new Cs(-32031,
    o.errorMessage??"Provider runtime headers were not applied before model request attempt.",
    {providerId:r.providerId,reason:r.reason,workspaceKey:t.workspaceKey});
  return o}}}
... ICs=18e4, z3n=-32022;
```

Request params schema (strict):

```js
RJt=m.enum(["model-request","captcha-retry"]),
NXn=m.object({requestId:fe,sessionId:fe,turnId:fe.optional(),workspace:Wi,
  modelSelection:mo, providerId:fe, accountAccess:LKt.optional(), reason:RJt}).strict()
LKt=m.object({type:m.literal("zhipu-account"),accountType:m.enum(["zai","bigmodel"]),
  mode:m.enum(["start-plan","individual-coding-plan","team-coding-plan","off-peak"]),
  entitled:m.boolean()}).strict()
```

Expected client result (this is where the apiKey now travels):

```js
VKe=m.discriminatedUnion("headersApplied",[
  m.object({headersApplied:m.literal(!0),
            requestAuth:m.object({apiKey:fe.optional(),headers:m.record(fe,fe).optional()}).strict(),
            errorMessage:fe.optional()}).strict(),
  m.object({headersApplied:m.literal(!1),errorMessage:fe.optional()}).strict()])
```

Engine side, per model attempt (`a(kp,"createRefreshRuntimeHeadersBeforeModelAttempt")` and
`a(sOe,"resolveModelForAttempt")`): for any provider whose
`providerConfig.access.type === "zhipu-account"` the refresh callback is **mandatory**; without it
the engine throws `Account model request auth is unavailable: <providerId>/<modelId>`
(`gt.ModelRequestAuthMissing`).

### C.8 Why the registry is empty in an `app-server` child

The app-server/agent bootstrap builds the registry with **no standalone options**:

```js
let w=e.env??process.env;
b=await q3e(w);
c.info("Worker Provider Registry 已就绪",{...,providerCount:b.snapshot.registry.providers.length});
```

Compare the headless `--prompt` CLI path, which *does* pass standalone (and therefore gets a
credential store + `O6n` = `createStandaloneProviderRuntimeHeadersPort`):

```js
w=await J(Z,o.skipUserConfig?{}:{standalone:{...ASe(e.stderr),...}});
```

With `t.standalone` undefined, `q3e` leaves `credentialStore` undefined, so the account source is the
empty default `y$` (`MutableAccountProviderConfigSource`, initial snapshot
`{revision:"empty-account-config-v1",basedOnZCodeBuiltinRevision:"uninitialized",providers:Nu.empty()}`)
and no `providerRuntimeHeadersPort` is returned from the registry. The per-session fallback is then
`r.providerRuntimeHeadersPort ?? F3n(e,t)` (`a(D8e,...)`) — i.e. **ask the protocol client**.

The host fills the account/entitlement side through a separate method,
`providerUpdateAccountConfig:"provider/updateAccountConfig"` → `a(O5n,"updateAccountProviderConfig")`:

```js
function O5n(e,t){let r=eo(FKe,t),n=G6n(r);
  if(!e.deps.syncAccountProviderConfig)throw new Cs(-32018,"Account Provider Config runtime is not configured");
  let o=await e.deps.syncAccountProviderConfig(n);
  return{receivedRevision:n.revision,providerCount:n.providers.keys().length,status:o?"received":"unchanged"}}
FKe=m.object({revision:fe,basedOnZCodeBuiltinRevision:fe,
  providers:m.record(m.string(),m.unknown()),
  states:m.record(m.string(),m.object({availability:m.enum(["available","pending","unavailable","unknown"]),
    entitled:m.boolean(),unavailableReason:P7e.optional(),current:m.boolean().optional(),
    connectionKey:m.string().optional(),effectiveAt:m.number().finite().optional()}).strict())}).strict()
```

and it refuses host overrides when the process manages its own standalone account
(`"Standalone Account 由本进程管理，不接收 Host 覆盖"`).

**No capability negotiation exists to opt out.** `runtime/capabilities` returns exactly
`{independentPlanState:!0}`. Unlike `session/requestRuntimePreferences` (which has an explicit
`-32601 || -32020` compatibility fallback to defaults), `interaction/requestProviderRuntimeHeaders`
has **no** not-implemented fallback: a client that answers `-32601` fails the turn.

### C.9 Envelope note (secondary)

The ZCode Protocol frame is **not** JSON-RPC 2.0; the union is strict and rejects a `jsonrpc` field:
`{"error":{"code":-32600,...,"message":"Unrecognized key: \"jsonrpc\""},...,"message":"Invalid ZCode Protocol message"}`
(`kaola-workflow/issue-74/evidence/live/03e-appserver-shim.out`). The Runner adapter already speaks
the bare `{id,method,params}` form; this only bites hand-written probes.

---

## D. CURRENT ADAPTER BEHAVIOR — `scripts/kaola-zcode-acp.py` (worktree issue-79, ADAPTER_VERSION `0.3.3`, 1603 lines)

| Lines | Element | Behavior |
| --- | --- | --- |
| 64-66 | constants | `DESKTOP_CONFIG_RELPATH=.zcode/v2/config.json`, `PLAN_CACHE_RELPATH=.zcode/v2/coding-plan-cache.json`, `CODING_PLAN_PROVIDER_IDS={builtin:bigmodel-coding-plan, builtin:zai-coding-plan}` |
| 80-96 | `DENIED_ENV` | 16 names (ANTHROPIC_*/OPENAI_*/ZCODE_* auth + ACP remote) asserted absent from the child env |
| 107-121 | `ENV_ALLOWLIST` | `HOME, PATH, TMPDIR, LANG, LC_ALL, LC_CTYPE, USER, LOGNAME, SHELL, TZ, TERM, KAOLA_ZCODE_ENTRY, KAOLA_ZCODE_NODE` — **no** `ZCODE_BUILTIN_PROVIDER_CONFIG_FILE` / `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE` |
| 146-149 | `register_secret` | adds any string ≥8 chars to `_SECRET_VALUES` |
| 151-163 | `redact` | recursive str/dict/list replace of registered secrets with `<redacted-credential>` |
| 166-168 | `log` | stderr only (stdout is the ACP channel), every message passes `redact()` |
| 181-206 | `resolve_runtime` | fail-closed: both values explicit, absolute, existing; node must be executable; no PATH/glob/download |
| 208-221 | `build_child_env` | `{k: os.environ[k] for k in ENV_ALLOWLIST if k in os.environ}`, pops `DENIED_ENV`, sets `ELECTRON_RUN_AS_NODE=1`, re-asserts no leak |
| 266-364 | `select_coding_plan_provider` | read-only `~/.zcode/v2/config.json`; eligible = id in `CODING_PLAN_PROVIDER_IDS`, `enabled is True`, non-empty `options.apiKey`, non-empty `models`, known `kind`, non-empty `options.baseURL`; `*-start-plan` and every non-coding-plan provider refused; >1 eligible → fail closed; `register_secret(key)`; annotates `plan_cache_status` from `coding-plan-cache.json` |
| 397-424 | `build_runtime_model` | builds `{revision, generatedAt, model:{providerId,modelId}, provider:{providerId,kind,apiFormat,label,source,baseURL,apiKey:{source:"inline",value:<secret>},models:[...]}}` |
| 449-450 | child spawn | `Popen([node, entry, "app-server", "--stdio"], env=build_child_env(), ...)` |
| 786-791 | `overlay_for` | resolves provider + wanted model, delegates to `build_runtime_model` |
| 793-821 | `materialize` | `session/create` with `{"workspace":…, "mode":…, "runtimeModel": overlay}` (**call site 1**), then `session/subscribe`, identity emit, `hydrate_settings` |
| 843-876 | `reregister_provider` | after resume: `session/setModel` with `{sessionId, model:{providerId,modelId}, "runtimeModel": …, persistAsWorkspaceLastUsed:false}` (**call site 2**) |
| 1275-1304 | `_resume_backend_session` | `session/resume` plain, and on failure retries `session/resume` **with** `"runtimeModel": overlay` (**call site 3**), then subscribe + hydrate + `reregister_provider` |
| 1432-1510 | `on_set_config_option` | `model` branch refuses a non-Coding-Plan provider and an unlisted model, then `session/setModel` with `"runtimeModel": build_runtime_model(...)` (**call site 4**) |

Redaction machinery is sound but narrowly scoped: only values registered by
`select_coding_plan_provider` are masked, and the overlay itself deliberately carries the plain
secret to the child over stdin (`apiKey:{source:"inline",value:…}`), never to a log.

The Issue #74 worktree `/tmp/kpr-i74-live-JM7IDB/checkout` (HEAD `431c012`) has a *tolerance* patch
only — it retries without the key when the error text contains both `runtimeModel` and
`Unrecognized` (lines 802-817, 867-874, 1331-1337). It does not supply a replacement mechanism, so
the turn then fails at `model_creation`.

---

## E. PRIOR EVIDENCE

### E.1 Working baseline (desktop 3.11.2, same CLI string 0.16.5)

`archive/bundle-51/uat-live-2026-09-16.md:7,111` and `archive/bundle-51/finalization-summary.md:7`
record live UAT with the `runtimeModel` overlay accepted, `ELECTRON_RUN_AS_NODE=1`, no auth env.
`archive/bundle-62/mission-list.md:23` records a full 6-scenario live pass with
`KAOLA_ZCODE_ENTRY=/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs` and provider
`builtin:bigmodel-coding-plan`, model `GLM-5.3`.

### E.2 3.12.3 failure — raw lines (Issue #74, 2026-09-18)

Bundled-config miss (identical in `03b-appserver-probe.err`, `03c-appserver-adapterenv.err`,
`03d-appserver-electron-node.err`):

```
无法定位 CLI ZCode Built-in Provider Config：/Applications/ZCode.app/Contents/Resources/glm/provider/zcode-builtin.json, /config/provider/zcode-builtin.json
```

`runtimeModel` rejection (`evidence/live/04-host-start-shim.json`, `12-host-resume.json`):

```
zcode error for session/create: {'code': -32602, 'data': {'name': 'ZodError',
 'message': '[\n  {\n    "code": "unrecognized_keys",\n    "keys": [\n      "runtimeModel" ...'},
 'message': 'Invalid params — (root): Unrecognized key: "runtimeModel"'}
```

Model gate after dropping the key (`evidence/live/06-host-handoff-send.json`, `08-host-handoff-send.json`):

```
"final_text": "[zcode turn failed] Select a model before continuing"
```

Raw backend telemetry (`evidence/live/probe-list/00-events-first-process.json`):

```json
{"method":"v4/telemetry/event","params":{"errorCode":"CONFIGURATION_ERROR",
 "errorMessage":"Select a model before continuing","kind":"turn.terminal",
 "sessionId":"sess_906aa4d5-75c0-445b-9b69-ba3a693e5703","status":"failed",
 "turnId":"turn_f612fe9e-644e-4aa1-9add-4c032bc05c15","turnPhase":"model_creation","version":1}}
```

Same capture also shows the server→client request the adapter *does* already face:

```json
{"id":"server-2","method":"session/requestRuntimePreferences",
 "params":{"scope":"user-execution","sessionId":"sess_906aa4d5-..."}}
```

Summary of the same run: `kaola-workflow/issue-74/evidence/live/15-live-results.md` — start became
`ready` only after a project-local shim of the `provider/zcode-builtin.json` layout; native id
`sess_2499f37a-fbbd-4046-a1c9-2d9aa896966d`; exact stop clean; `--resume` then `Session not found`.

### E.3 /tmp survivors

- `/tmp/kpr-i74-live-JM7IDB/` — only `checkout/` (another run's worktree, HEAD `431c012`, read-only).
- `/tmp/kpr-zcode-live-HYway8/` — only a bare `.git/`; no captures.
- No other `/tmp/kpr-zcode-live-*` or `/tmp/kpr-i74-live-*` directories exist.
- `archive/issue-51` does not exist (the work is archived as `bundle-51`).
  `archive/issue-65` and `archive/issue-70` contain the entry/node values (B.1) but no 3.12 failure captures.

### E.4 Current desktop registry state (redacted structure only)

`~/.zcode/v2/config.json` → `provider` with 6 entries. Exactly one Coding Plan is enabled:

```
builtin:bigmodel-coding-plan  name="BigModel - Coding Plan" kind=anthropic enabled=true
    options.baseURL="https://open.bigmodel.cn/api/anthropic"  options.apiKey=<REDACTED>
    models: GLM-5.3, GLM-5.3-Flash
builtin:bigmodel-start-plan   enabled=true  models={}          (refused by the adapter: start-plan)
builtin:zai-coding-plan       enabled=false systemDisabledReason="oauth_provider_inactive"
builtin:zai-start-plan        enabled=false systemDisabledReason="oauth_provider_inactive"
builtin:bigmodel              (API-key, no `enabled` field)    (refused: pay-as-you-go)
builtin:zai                   enabled=false                    (refused: pay-as-you-go)
```

`~/.zcode/v2/coding-plan-cache.json`:
`builtin:bigmodel-coding-plan → {"status":"available"}`, `builtin:bigmodel-start-plan → available`,
both `zai` entries `{"status":"unavailable","reason":"coding_plan_not_authenticated"}`.

Present but **never opened**: `credentials.json` (2315 B, 0600), `setting.json` (2350 B, 0644),
`provider_config.json` (206 B, 0600), `bot-config.v3.json`, `bot-state.v3.json`.

---

## What could NOT be established here

1. **Whether supplying the two env vars alone makes the registry usable.** Proving it requires
   starting an `app-server` child, which this mission forbids. Static reading says it is necessary
   but not sufficient: the registry would load rules + personal config, but zhipu-account providers
   still need `provider/updateAccountConfig` (entitlement/state) and
   `interaction/requestProviderRuntimeHeaders` (per-request `requestAuth.apiKey`).
2. **The exact provider-instance shape `provider/updateAccountConfig` expects.** Its `providers`
   field is `m.record(m.string(), m.unknown())` re-parsed by `$mr(...)` inside
   `a(G6n,"parseProcessAccountProviderConfigSnapshot")`; the inner provider schema was not fully
   traced, and `G6n` additionally requires `states[<id>].current` to be a boolean for any entitled
   `zhipu-account` provider.
3. **The content/role of `~/.zcode/v2/provider_config.json`** — deliberately not read (0600, named
   by `ESe` as the personal provider config). Its exact relation to `~/.zcode/v2/config.json` is
   therefore inferred, not measured.
4. **Whether the desktop app sets the two env vars when it spawns its own CLI child.** Not
   observable without inspecting a running desktop process, which would require touching live
   processes.
5. **Which ZCode release first removed `runtimeModel`.** Only the two endpoints are measured here:
   accepted at desktop 3.11.2 (archived), absent at 3.12.3 (0 bundle occurrences).
