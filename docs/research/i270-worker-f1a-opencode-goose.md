# KPR #270 — Family-1a breadth: opencode-ai/opencode + block/goose (read-only)

Read-only via GitHub API/raw, 2026-10-07; no install/deploy. `[SV]`=SOURCE_VERIFIED (file read at pin), `[RM]`=README_MENTIONED.

## A. github.com/opencode-ai/opencode
Pin: `main` @ `73ee493265acf15fcd8caab2bc8cd3bd375b63cb` (2025-09-18), tree `d3fe3eac5b3f3893e5e58ecc502a5eaca78fbbea`. Workspace: Go modules (`go.mod`).
- **Identity [SV]:** `archived: true`; README title "Archived: Project has Moved"; continuation named Crush `[RM→README, not source-verified]`. This is the Go TUI agent, NOT the active opencode CLI KPR runs (`sst/opencode`→`anomalyco/opencode` @ `ecc4916b`, plugin DSL `packages/core/src/config/plugin.ts` `Plugins=Schema.Array` `[SV]`). Use as provenance only.
- **License [SV]:** root `LICENSE`=MIT, "Copyright (c) 2025 Kujtim Hoxha"; partition `internal/lsp/protocol/LICENSE` (vendored LSP protocol).
- **Role/module lifecycle [SV]:** no plugin/extension loader exists. Sole extension surface = MCP servers, declared `mcpServers: map[string]MCPServer{command,args,env,type:stdio|sse,url,headers}` (`internal/config/config.go`); loaded per call by `internal/llm/agent/mcp-tools.go` `GetMcpTools` (`NewStdioMCPClient` / SSE client with headers). Nearest "plugin" = custom `.md` command files `[RM]`.
- **Provider [SV]:** `Provider` interface {`SendMessages`,`StreamResponse`,`Model`}; `NewProvider(name)` is a hardcoded compile-time `switch` over 9 providers (`internal/llm/provider/provider.go`); config `Provider{apiKey,disabled}`. Not a registration point — new providers need edit+rebuild.
- **Shared data/multi-process [SV]:** SQLite via `database/sql`+`ncruces/go-sqlite3`, `PRAGMA journal_mode=WAL` (`internal/db/connect.go`); one `*sql.DB`, no cross-process lock/coordinator.
- **Cross-version [SV]:** numbered SQL migrations `internal/db/migrations/*.sql`; embedded schema.
- **Secrets [SV]:** per-provider `apiKey` from config/env (`setProviderDefaults`, e.g. `ANTHROPIC_API_KEY`); plain config file.
- **Fit/misfit:** misfit — no declarative contract, no capability/version/degradation, single-process DB, unmediated secrets. No reusable mechanism beyond "MCP as sole extension protocol".

## B. github.com/block/goose
Pin: requested `block/goose` redirects to `aaif-goose/goose` `[SV]`; `main` @ `f9c18a81952e8895b6f2d88b0f4569f3975034af` (2026-10-07), tree `694c2f4f0cef9f9c83db01312d4f605a50b5fb9f`; Rust workspace v1.54.0.
- **License [SV]:** root `LICENSE`=Apache-2.0; partition `crates/goose-mcp/licenses/*.license` (bundled chart.js/d3/leaflet/mermaid).
- **Role/module lifecycle [SV]:** extensions = MCP servers. `ExtensionConfig` (`crates/goose/src/agents/extension.rs`) serde-tagged enum `stdio|builtin|platform|streamable_http`; `Envs` blocks 31 hijack keys (PATH, LD_PRELOAD, NODE_OPTIONS…). Runtime owner `ExtensionManager` (`agents/extension_manager/mod.rs`): immutable per-scope `ExtensionSet`→`ExtensionLease` (`lease.rs`), `add_extension`/`remove_extension`/`apply(ExtensionMutation)`; platform extensions (developer, analyze…) run in-process.
- **Providers [SV]:** `config/providers.rs` (`ProviderEntry`, active provider) + `goose-providers/src/declarative.rs` `DeclarativeProviderConfig` (`include_dir!` JSON defs; `api_key_env` or `auth.command` exec-not-shell credential fetch).
- **Shared data/multi-process [SV]:** YAML config; writes take exclusive `fs2` lock on `<file>.lock` (`config/base.rs:654 lock_exclusive`) then temp-file + `std::fs::rename` (atomic); `Arc<Mutex>` serializes in-process.
- **Cross-version [SV]:** `config/migrations.rs` `run_migrations` (platform-extension + flat→structured provider), plus non-destructive `run_read_migrations`.
- **Secrets [SV]:** system keyring (`keyring::Entry`) with `GOOSE_DISABLE_KEYRING` file fallback `secrets.yaml`; precedence env>keyring>file; `write_private_file` (private temp + atomic persist).
- **Fit/misfit:** fit — declarative typed extension enum + lease lifecycle, data-driven providers, cross-process lock + atomic replace, versioned migrations, keyring-with-fallback all map to KPR O1–O4. Misfit — Rust in-process agent; no module contract-version/capability/degradation manifest; payload shape is MCP, not arbitrary KPR modules; Apache-2.0 → reimplement patterns, don't vendor.
