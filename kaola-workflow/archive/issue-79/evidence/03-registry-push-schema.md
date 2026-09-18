# Issue #79 — Mission 2b: registry-push and account-provider schema (INSTALLED ZCode 3.12.3)

Source of every quote below: `/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`
(11,416,833 bytes, 3,583 lines, minified) and the rules-only bundled table
`/Applications/ZCode.app/Contents/Resources/config/provider/zcode-builtin.json`
(schemaVersion 1, revision 28, 0 secret literals).

Provenance note: the investigator subagent that performed these 72 bundle extractions stopped
before writing its report. Nothing was re-run; these findings were recovered verbatim from that
agent's own recorded tool results, so this file is its evidence, not a second investigation.
Recovered 2026-09-18.

Read-only throughout. No process started. `~/.zcode/v2/credentials.json`, `setting.json` and
`~/.zcode/v2/provider_config.json` were never opened. No secret value appears in this file.

---

## 1. Provider id and model ids for `session/setModel` — VERIFIED

Our desktop registry id `builtin:bigmodel-coding-plan` is NOT what the app-server registry uses.
The bundled table's `providerRules` (8 entries, all `account:*`) contains:

```json
{
 "providerId": "account:bigmodel-individual-coding-plan",
 "providerName": "BigModel Individual Coding Plan",
 "config": {
  "group": "bigmodel-family",
  "builtinModelIds": ["GLM-5.3", "GLM-5.3-Flash"],
  "access": {"type": "zhipu-account", "mode": "individual-coding-plan", "accountType": "bigmodel"},
  "api": {"type": "anthropic-messages", "baseUrl": "https://open.bigmodel.cn/api/anthropic"},
  "logo": {"type": "builtin", "key": "bigmodel"}
 }
}
```

The id constant table and its predicate:

```js
...bigmodelTeamCodingPlan:"account:bigmodel-team-coding-plan",bigmodelStartPlan:"account:bigmodel-start-plan"};
a(PQ,"isBuiltinModelProviderId");
function PQ(e){return e===Ki.zaiIndividualCodingPlan||e===Ki.zaiTeamCodingPlan||e===Ki.zaiStartPlan
  ||e===Ki.bigmodelIndividualCodingPlan||e===Ki.bigmodelTeamCodingPlan||e===Ki.bigmodelStartPlan}
```

**Exact literals to send for the GLM Coding Plan:**
- `providerId` = `account:bigmodel-individual-coding-plan`
- `modelId` = `GLM-5.3` (or `GLM-5.3-Flash`) — exact case as listed in `builtinModelIds`

Model selection schema (`mo`), used by both `session/setModel` and the runtime-headers request:

```js
mo=m.object({providerId:m.string().trim().min(1),modelId:m.string().trim().min(1),
  options:m.object({reasoningLevel:m.string().trim().min(1).optional()}).strict().optional()}).strict()
```

`reasoningLevel` for GLM-5.3 accepts `{"values":["low","high","max"]}` (from `modelConfigRules`,
`maxOutputTokens.max` 128000). Sending no `options` is valid since it is `.optional()`.

## 2. `provider/updateAccountConfig` — VERIFIED PRESENT

The method exists in the installed 3.12.3 build. Only two `provider/*` methods exist:

```
"provider/testModelConnectivity"
"provider/updateAccountConfig"
```

with `zcodeProviderUpdateAccountConfigParamsSchema:()=>FKe` and
`zcodeProviderUpdateAccountConfigResultSchema:()=>AXn` exported.

Validator `G6n`, registered as `parseProcessAccountProviderConfigSnapshot`:

```js
function G6n(e){
  let t=e.revision.trim(); if(!t) throw new Error("Account Config revision 不能为空");
  let r=e.basedOnZCodeBuiltinRevision.trim(); if(!r) throw new Error("Account Config Built-in revision 不能为空");
  let n=$mr(e.providers);
  for(let[o,i] of n.entries())
    if(PQ(o) && i.access?.type==="zhipu-account" && i.access.entitled
       && typeof e.states?.[o]?.current!="boolean")
      throw new Error(`Account State 缺少 current: ${o}`);
  return Object.freeze({revision:t,basedOnZCodeBuiltinRevision:r,providers:n,...e.states?{states:e.states}:{}});
}
```

Provider map parser `$mr`, registered as `parseAccountProviderConfigMap`:

```js
function $mr(e){let t=xn.record(xn.string().min(1),aSo).parse(e);
  return new Nu(Object.entries(t).map(([r,n])=>[r,_ft(n)]))}
aSo=jT.pick({builtinModelIds:!0}).extend({access:uft.pick({type:!0,entitled:!0}).nullable().optional()});
```

**Key casing settled from the installed side: `basedOnZCodeBuiltinRevision`** (capital `Z`, capital
`C`). Upstream's comment spelling `basedOnZcodeBuiltinRevision` is wrong for this build.

**Resulting params shape to send:**

```json
{
  "revision": "<non-empty string>",
  "basedOnZCodeBuiltinRevision": "<non-empty string, see section 4>",
  "providers": {
    "account:bigmodel-individual-coding-plan": {
      "builtinModelIds": ["GLM-5.3", "GLM-5.3-Flash"],
      "access": {"type": "zhipu-account", "entitled": true}
    }
  },
  "states": {"account:bigmodel-individual-coding-plan": {"current": true}}
}
```

`states[id].current` is a REQUIRED boolean for any entitled zhipu-account provider — omitting it
throws `Account State 缺少 current`. Note `aSo` picks ONLY `builtinModelIds` and `access.{type,entitled}`;
`.parse` on a zod object strips unknown keys, so no baseURL/apiKey channel exists here.

## 3. Which builtin path to inject, and both-or-neither — VERIFIED (with one open sub-point)

`Fy`, registered as `NodeZCodeBuiltinProviderConfigSource`:

```js
constructor(t){let r=t.bundledFilePath.trim();
  if(!r) throw new Error("ZCode Built-in bundledFilePath 不能为空");
  this.#e=r;
  this.#t=t.activeFilePath?.trim()||r;
  this.#r=(0,ihr.createHash)("sha256").update((0,b$.resolve)(this.#t)).digest("hex");
  this.#n=t.watch!==!1}
async read(){...try{await this.#u(); t=await Du(this.#t,()=>this.#l())}catch{t=nhr(await Pft(this.#e),null)}
  this.#c??=Sre(t); return TSo(t,this.#r)}
```

So `bundledFilePath` falls back to itself as the active path when no separate active path is given.
We inject the `.app` bundled table `<Resources>/config/provider/zcode-builtin.json`, which is the
path the CLI's own probe misses (see `evidence/02-local-ground-truth.md`).

## 4. Revision construction and validation — VERIFIED (sha256 is over the PATH STRING)

```js
function TSo(e,t){return Object.freeze({revision:`zcode-builtin:${e.revision}:${t}`,
  providers:e.config.providers,providerTemplates:e.config.providerTemplates,models:e.config.modelConfigRules})}
function Sre(e){return `${e.revision}:${ER(e)}`}   // ER = serializeZCodeBuiltinRelease
```

`t` is `#r` = `sha256(path.resolve(activeFilePath))` — **a hash of the resolved PATH STRING, not of
the file content**. So the app-server's own builtin revision string is
`zcode-builtin:<release.revision>:<sha256 of the resolved active path>`.

Measured candidates on this machine (all revision 28):

| resolved path | sha256(path) | full revision string |
|---|---|---|
| `/Applications/ZCode.app/Contents/Resources/config/provider/zcode-builtin.json` | `8f54ff88…fab1c` | `zcode-builtin:28:8f54ff88821cb0f70c213894cd6e3434966f570e74b53e061aa19778f79fab1c` |
| `~/.zcode/v2/runtime/provider/darwin-aarch64/3.12.3/endpoint-78d7c3…/zcode-builtin.json` | `232456…e06dc` | `zcode-builtin:28:232456098d1e1608293ba2a05794395eca40adc3b9ddd4f1600f22eacf5e06dc` |
| `~/.zcode/v2/runtime/provider/darwin-aarch64/0.0.0-dev/endpoint-78d7c3…/zcode-builtin.json` | `e8b278…259a79` | `zcode-builtin:28:e8b278f423ae14bd891ed89342e0b98dc9a9ba8b1e5bb6b71f0af3eb77259a79` |

`G6n` itself validates `basedOnZCodeBuiltinRevision` ONLY as non-empty after trim. Whether any
downstream consumer compares it against the app-server's own computed string — and therefore which
of the three candidates above we must send — is **NOT ESTABLISHED statically**. This is the single
value that must be confirmed against a live app-server rather than asserted.

## 5. `access.type === "zhipu-account"` gating — VERIFIED

`_ft` (`createProviderConfig`) routes zhipu-account access to a distinct class:

```js
function _ft(e){return new ad({...e,
  access:e.access==null?e.access:e.access.type!=="zhipu-account"?new zT(e.access):new Vw(e.access),
  api:e.api==null?e.api:new j5(e.api)})}
```

For a zhipu-account provider the runtime-headers callback is MANDATORY — there is no default:

```js
...t.providerConfig.access.type==="zhipu-account"?d??(async()=>{throw ...
```

and the model attempt path enforces it:

```js
if(!n.headersApplied||!n.requestAuth)
  throw new Error("Provider request auth was not returned before model request attempt.");
return e.resolveModel(n.requestAuth)
```

## 6. `interaction/requestProviderRuntimeHeaders` — VERIFIED

Params (`NXn`) and response (`VKe`):

```js
RJt=m.enum(["model-request","captcha-retry"]),
NXn=m.object({requestId:fe,sessionId:fe,turnId:fe.optional(),workspace:Wi,modelSelection:mo,
  providerId:fe,accountAccess:LKt.optional(),reason:RJt}).strict(),
$Xn=m.object({requestId:fe,sessionId:fe,workspace:Wi}).strict(),   // cancelled
VKe=m.discriminatedUnion("headersApplied",[
  m.object({headersApplied:m.literal(!0),
    requestAuth:m.object({apiKey:fe.optional(),headers:m.record(fe,fe).optional()}).strict(),
    errorMessage:fe.optional()}).strict(),
  m.object({headersApplied:m.literal(!1),errorMessage:fe.optional()}).strict()])
```

`requestAuth` is REQUIRED in the `headersApplied:true` branch (`.strict()`, not optional), and the
consumer rejects a missing one. `apiKey` and `headers` are each individually optional and are
alternatives/additions: `{headersApplied:true, requestAuth:{apiKey:"<secret>"}}` is sufficient and
is the shape to send. `.strict()` means no extra keys.

Workspace schema `Wi` (shared with session methods):

```js
Wi=m.object({workspacePath:uo,workspaceIdentity:uo.optional(),remoteSessionId:uo.optional(),workspaceKey:uo}).strict()
```

## 7. Call ordering — PARTIALLY ESTABLISHED

`provider/updateAccountConfig` is validated by a function named
`parseProcessAccountProviderConfigSnapshot`, and the registry runtime entry point is
`q3e` / `startProcessProviderRegistryRuntime` — both named "Process", indicating the snapshot is
**per app-server process/connection, not per session**. That makes the order:

1. `initialize`
2. `provider/updateAccountConfig` (once per backend process, before any session needs a model)
3. `session/create` (no model key)
4. `session/setModel` with `account:bigmodel-individual-coding-plan` / `GLM-5.3`
5. `session/subscribe`, then `session/send`
6. answer `interaction/requestProviderRuntimeHeaders` on every model request during the turn

The per-process inference rests on the symbol names, not on a quoted call graph.

---

## NOT ESTABLISHED

1. **Which of the three revision strings `basedOnZCodeBuiltinRevision` must carry** — i.e. whether
   the app-server's active path becomes our injected bundled path or a version-keyed runtime copy.
   Static reading cannot settle it; must be observed live. (Highest-risk open item.)
2. Whether setting both env vars SUFFICES to make `app-server` start — static reading says the
   injection is necessary, not that it is sufficient. Needs a real start.
3. The result schema body of `zcodeProviderUpdateAccountConfigResultSchema` (`AXn`) was not quoted.
4. Whether `provider/updateAccountConfig` must precede `session/create` or merely precede the first
   model request.
5. Contents/role of `~/.zcode/v2/provider_config.json` (0600, deliberately never opened).
6. Whether the desktop app sets these env vars for its own CLI child.
7. Which release first removed `runtimeModel` (only 3.11.2 accepted / 3.12.3 absent are measured).
