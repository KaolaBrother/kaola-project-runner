# Issue #75 capability evidence matrix

Reconciled 2026-09-18 by the resumed bundle-75 worker after the prior worker was
stopped mid-item. Every row names its evidence class:

- **binary-verified**: read-only static inspection of the installed binary/bundle
  in this session (no execution, no credential access).
- **doc-verified**: official documentation fetched/quoted this session.
- **outer-verified**: verified fact carried by the Issue #75 comments.
- **worker-reported**: prior worker's recorded claim, consistent with the
  binary-verified rows but not re-derived end to end.

## Codex (codex-cli 0.153.4, installed via npm)

| Claim | State | Evidence |
|---|---|---|
| `SessionStart` matcher source `compact` exists | VERIFIED | binary-verified: installed binary contains the contiguous source list `startupresumeclearcompact` (matches `SessionStartSource` enum {Startup,Resume,Clear,Compact} in `codex-rs/hooks/src/events/session_start.rs`); doc-verified: developers.openai.com/codex/hooks |
| Compact source is delivered before the next model request | VERIFIED | doc-verified: openai/codex PR #21272 — pending SessionStart sources are queued FIFO and drained before the next model request; integration coverage asserts `resume`→`compact` stacking reaches `additionalContext` |
| Hook output reaches the model as context | VERIFIED | doc-verified: `command` hook stdout becomes `additionalContext` (developer context); `additionalContextLimit` caps inline bytes, overflow saved to disk + preview; command runs with session `cwd` |
| Hook config sources | VERIFIED | doc-verified: `~/.codex/hooks.json`, `~/.codex/config.toml [hooks]`, `<repo>/.codex/hooks.json`, `<repo>/.codex/config.toml`, enabled-plugin `hooks/hooks.json`; all matching hooks from all sources load (merge, never replace); project layer needs project trust |
| Trust model | VERIFIED | doc-verified: non-managed hooks need review/trust recorded against the hook hash; `/hooks` CLI inspects; `--dangerously-bypass-hook-trust` runs enabled hooks without persisted trust for one vetted invocation |
| Local precedent for this exact mechanism | VERIFIED | local-verified: `~/.codex/hooks.json` carries `kaola-workflow:compact-context` (`matcher:"compact"`, `command:"cat <payload.md>"`, `timeout:5`); `~/.codex/config.toml [hooks.state]` records per-entry state keyed `hooks.json:session_start:0:0` — a receipt channel for evidence |
| Isolated verification path | AVAILABLE | real `CODEX_HOME` (auth + foreign hooks untouched) + scratch `<repo>/.codex/hooks.json` carrying only our entry + `--dangerously-bypass-hook-trust` + TUI `/compact` via tmux drive; no user-global write at all |

## ZCode (0.16.5, `/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`, 11 416 833 B)

| Claim | State | Evidence |
|---|---|---|
| User `~/.zcode/cli/config.json` `hooks.events` is a runnable source, gated by `hooks.enabled` | VERIFIED | binary-verified: `sourceEnabled:n.hooks.enabled` feeds the runnable set; `gVi` iterates `config.events`; `hooksRoot` carries `enabled`/`timeoutMs`/`maxOutputBytes`; `nativeConfigDir:".zcode/cli"` + `nativeConfigFileName:"config.json"` are declared constants |
| Enabled-plugin `hooks/hooks.json` is a runnable source | VERIFIED | binary-verified: `i_i=(0,join)("hooks","hooks.json")` + `listPluginHookSources`/`attachPluginToHook`/`canRunPluginHooks` |
| Project `<workspace>/zcode.json` / `.zcode/config.json` hooks are not an executable source in this host path | VERIFIED (mechanism) | binary-verified: `configFileKind` enum `["zcode.json",".zcode/config.json","explicit"]` and `discoverWorkspaceHookConfigPaths` show workspace hook files ARE discovered into `workspaceHookSnapshot`, but every dispatch passes `workspaceHookAdmission.evaluateDispatch`; headless block reasons include `workspace_hooks_feature_disabled` and a not-trust-capable host → consistent with outer-verified "project hooks 整体被忽略" (Issue comment 2026-09-18T11:50Z) |
| Config is snapshotted at session start | VERIFIED | binary-verified: `workspaceHookSnapshot` (taken once, consulted per dispatch); outer-verified |
| `SessionStart(compact)` actually fires | **NEGATIVE** | binary-verified: `runSessionStartHooks` (internal `xkn`) has exactly two call sites — `"startup"` and `"resume"`; no `"compact"`/`"clear"` call site exists; `sessionStartHookRan` makes even those once-per-session; `app.asar` holds no call site. Doc-advertised `compact` matcher can never match in 0.16.5 |
| `runtimeModel` overlay accepted | **NEGATIVE** | binary-verified: `runtimeModel` 0 hits in the 0.16.5 bundle; `model.providerId` 8 hits — the new path is `model:{providerId,modelId}` + account credential store (worker-reported, consistent) |
| `session/create` returns `app-server exited` | CONFIRMED, unfixed | outer-verified (Issue comment 11:50Z: two repos, exact stop, `residual_pids=[]`); binary-verified levers: `ZCODE_STORAGE_DIR`×4, `ZCODE_DATA_BASE_DIR`×4, `ZCODE_BUILTIN_PROVIDER_CONFIG_FILE`×1 exist; worker-reported diagnosis: provider-config lookup fails for the `glm/zcode.cjs` entrypoint. Live retest is blocked on #79 (comment 14:41Z) |
| Current local `~/.zcode/cli/config.json` hooks state | `{"hooks":{}}` | local-verified: `hooks` key present, `enabled` unset — user-layer hooks currently NOT enabled |
| Fallback carrier candidates if `SessionStart` stays compact-blind | CANDIDATE, unverified | binary-verified: `runUserPromptSubmitHooks`/`runStopHooks`/`runPostToolUseHooks` entry points exist; UserPromptSubmit is the minimal pre-reasoning path to verify once #79 unblocks live probing |

## Boundary for this issue

- Codex carrier: `SessionStart(matcher:"compact")` + short Runner-owned payload via
  merge-safe edit of `${CODEX_HOME}/hooks.json` — mechanism fully verified above.
- ZCode carrier: docs-claimed `SessionStart(compact)` is disproven by the binary;
  the real carrier decision needs live compact-behavior proof that is blocked on
  #79 (`session/create` → `app-server exited`). No ZCode hook deliverable ships
  from this frontier; findings + candidate path are recorded instead.
