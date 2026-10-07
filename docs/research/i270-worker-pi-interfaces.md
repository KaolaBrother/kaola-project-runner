# KPR issue #270 — pi `chord` + `durable` interface review

Read-only. Source: github.com/earendil-works/pi @ `main` (tree `eb326d2`), fetched 2026-10-07. Files: `packages/chord/src/{api,index,types}.ts`; `packages/durable/README.md`, `docs/spec.md`, `docs/pico-v5-chord-usage.md`, `src/index.ts`, `src/documents.ts`, `src/harness/{registry,define}.ts`, `src/storage/sqlite/database.ts`, `src/testing/*`. No install, clone, or code change.

## Chord (`@earendil-works/chord`) — composition/plugin
- `api.ts` exports `defineFacet`, `createFacetHost`, `createStaticFacetLoader`, `combineFacetLoaders`, `defineService`, `createRemoteServiceBinding`, `replicatedState`.
- Facet = `{ id, setup(env) }`. `FacetEnvironment` is the registration surface: `use`/`observe` (declare deps), `provide` (singleton) / `provideMany` (keyed spawner), `replicatedState(initial)`, `own(cleanup)`, `onActivate` (after deps ready), `onDeactivate`.
- `FacetHost` = `{ services, reload(facets), dispose }`; reload swaps facets by matching `id`. `FacetLoader.load(): LoadedFacets` + `combineFacetLoaders` allow pluggable facet sources.
- `defineService<T>(id,{local:true})` or a remote contract; `Service<T>={id,local}`; reserved `$chord.` namespace.
- Pluggable state: `ReplicatedStateSource<T>.attach()` (atomic snapshot + ordered frames); `MutableReplicatedState.change/replace`; `ReplicatedState` = `value` + `subscribe(value,context,delivery)`. Chord "only publishes references; never applies or re-diffs." Pluggable wire: `RemoteServiceTransport.invoke/subscribe`; adapter owns transport/framing/serialization; values must be strict JSON.

## Durable (`@earendil-works/pi-durable`) — registration, storage, conformance
- Extensions: `defineExtension({name,tools,sections,hooks,wraps,tasks})`; `createRegistry()` → `Registry.install/uninstall`. Named; reinstall replaces in place; conversations store extension *names*, resolved against the current snapshot. Built-ins `GenerationTask/ToolTask/CompactionTask` always present; install validates unique tool/section keys.
- Typed records: `defineDoc<T>({kind,version,scope,history,fork,initial,migrate,checkpointWhen})` + `defineDocFamily`. Scopes: session / conversation (latest|rewindable; fork current|initial|asOf) / task. `defineTask`; branded numeric ids never reused; typed access validates scope/history/version and rejects ambiguous copies.
- Storage: `Storage` interface; Memory, SQLite, JSONL, Cloudflare Durable Objects. Portable cores plus async `SqliteDatabase`/`SqliteExecutor` facades (`exec/run/get/all/transaction/close`). Atomic-commit invariant; Session owns one mutation line; **"One process owns a storage at a time; there is no cross-process locking."**
- Conformance: `registerStorageConformance` / `registerEnvConformance` (`/testing`), built from runner-independent `createStorageConformance` / `createEnvConformance`. Storage cases check: root-ID immutability; atomic mixed commits + rollback; detached records; prototype-key safety; entry index/cursor order; conversation pagination/owner edges; deep-fork history; asc/desc table scans; task replacement + filters; request-ID indexing; passive writes; rewindable/half-open document lifetimes; version-transition base rule; logical-address indexing. Env cases: readers, watch, argv exec, windowing, timeout/abort, symlinks.

## Fit / misfit vs KPR contract needs
**Fit.**
- `defineDoc` + typed tokens + `registerStorageConformance` is a concrete reference for KPR's O1/O4: versioned typed records with a shared, runner-independent conformance registration.
- Scoped docs (session/conversation/task) with retirement map onto KPR record ownership/lifetime (dispatch index, mission ledger).
- Registry + reload/reinstall-by-name and `FacetLoader` composition model KPR optional modules (absent → skipped/degraded) and runtime selection.
- Single-writer intent aligns: "Pico remains the sole mutator"; one Session mutation line.

**Misfit.**
- Language/runtime: TS/Node in-process vs KPR's Bash+Python over ACP — not reusable as a dependency.
- Durable's single-writer is in-process only, no cross-process locking — the inverse of KPR's multi-agent shared-file world; its guarantee does not transplant.
- Durable is a full agent harness (conversations, turns, tools, compaction); KPR artifacts are small JSON — reuse imports unwanted semantics.
- Chord "modules" are code bundles, not declarative manifests with contract-version/capability/degradation fields — KPR's O3 is not directly provided.
- Chord requires strict JSON; KPR's governed class must exclude human prose/Git evidence.
- Both packages marked experimental (API changes without notice) → study the pattern, not a dependency.
