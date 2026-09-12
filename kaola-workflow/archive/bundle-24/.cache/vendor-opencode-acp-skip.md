# Vendor lookup: OpenCode ACP skip-all / auto-approve

Lookup date: 2026-09-13 (no clock on docs pages; GitHub activity around this window is dated 2026-09).
Target version: OpenCode **1.18.29** (live CLI on the host). Sources below match that tag where noted; live `opencode.ai/docs` has no version stamp.

## Conclusion

Current OpenCode does **not** document an `opencode acp` skip-all / auto-approve knob equivalent to TUI/`run` `--auto` (“auto-approve permissions that are not explicitly denied”). Official CLI and ACP docs for 1.18.29 list `opencode acp` flags as `--cwd` plus network options only. Help-text snapshots and `packages/opencode/src/cli/cmd/acp.ts` at tag `v1.18.29` and current `dev` likewise omit `--auto` / `--yolo` / `--dangerously-skip-permissions`. ACP `configOptions` at that tag advertise `model`, optional `effort`, and `mode` (`build`/`plan`); they do not advertise `auto`/`yolo`. Upstream GitHub issue #47918 (opened 2026-09-08, still open) requests that missing ACP `configOptions` toggle and reports that on the official **v1.18.29** Windows binary `auto`/`yolo` return JSON-RPC `-32602`. Agent Client Protocol allows **clients** to auto-allow `session/request_permission`; that is a client policy, not an OpenCode ACP agent flag. Static OpenCode `permission: "allow"` / `OPENCODE_PERMISSION` is a different, config-level allow/deny mechanism and is not documented as ACP `--auto`.

Do not treat this as measured CLI behavior of `opencode acp --auto` or `opencode --auto acp`.

## Upstream

| Claim | URL opened | Date verified on page | Supporting sentence |
| --- | --- | --- | --- |
| Canonical repo is `anomalyco/opencode` (not a separate `sst/opencode` tree). | https://github.com/anomalyco/opencode | Fetched 2026-09-13; GitHub README “Latest commit”/history on `dev`; npm/docs point here. | README: “The open source AI coding agent.” Install: `brew install anomalyco/tap/opencode`. |
| `https://github.com/sst/opencode` resolves to the same `anomalyco/opencode` project page. | https://github.com/sst/opencode | Fetched 2026-09-13 (page body is `anomalyco/opencode`). | Page title/header: “GitHub - anomalyco/opencode: The open source coding agent.” |
| v1.18.29 exists on that repo. | https://github.com/anomalyco/opencode/releases/tag/v1.18.29 | GitHub: “released this 04 Sep 23:47” (2026). Tag `v1.18.29`, commit `16747470f976aca3d362ad730bcd3fe82ecc2c9a`. | Heading “v1.18.29”; notes are unrelated Codex OAuth filtering (no ACP `--auto`). |

## Claims and sources

| Claim | URL actually opened | Publication / revision date | Quoting sentence |
| --- | --- | --- | --- |
| TUI `--auto` means auto-approve permissions that are not explicitly denied. | https://opencode.ai/docs/cli | Live docs page has **no** revision date. Same text in tag `v1.18.29` source: https://github.com/anomalyco/opencode/blob/v1.18.29/packages/web/src/content/docs/cli.mdx (file history on that tag includes 2026-08-26). | TUI flags: “`--auto` — Auto-approve permissions that are not explicitly denied”. Same wording under `opencode run`. |
| `--auto` is documented for TUI and `run`, not as a global flag. | https://opencode.ai/docs/cli (Global Flags table) | Same as above. | Global flags listed: `--help`, `--version`, `--print-logs`, `--log-level`, `--pure` only. |
| `opencode acp` documented flags do **not** include `--auto`. | https://opencode.ai/docs/cli#acp and v1.18.29 `cli.mdx` | Live: no date. Tag source last listed commit for `cli.mdx` on `v1.18.29`: 2026-08-26 (`fd9bd448…`). | “Start an ACP (Agent Client Protocol) server.” Flags: `--cwd`, `--port`, `--hostname`, `--mdns`, `--mdns-domain`, `--cors`. |
| Official ACP editor config is `opencode` + `["acp"]` only. | https://opencode.ai/docs/acp | Live: no date. Source `packages/web/src/content/docs/acp.mdx` on GitHub. | “To use OpenCode via ACP, configure your editor to run the `opencode acp` command.” Zed example: `"args": ["acp"]`. |
| ACP docs claim permissions work via ACP; they do not document skip-all. | https://opencode.ai/docs/acp | Live: no date. | “OpenCode works the same via ACP as it does in the terminal. All features are supported: … Agents and permissions system”. Note: some slash commands unsupported; no `--auto`. |
| Auto mode docs cover TUI/`run` only. | https://opencode.ai/docs/permissions | Live: no date. Source last commit on `v1.18.29` tree: 2026-06-30 (`0a5bed2b…`, “feat(tui): add yolo permission mode (#33279)”). | “Start OpenCode with `--auto` to automatically approve permission requests that are not explicitly denied.” Examples: `opencode --auto` and `opencode run --auto "…"`. “In the TUI, open the command palette and select **Enable auto-approve permissions**…” |
| Static config can set `"permission": "allow"` (not the same as `--auto`). | https://opencode.ai/docs/permissions | Same as above. | “You can also set all permissions at once: `{ "permission": "allow" }`.” Actions: `"allow"` — “run without approval”. |
| `OPENCODE_PERMISSION` is inlined JSON permissions config, not an ACP auto flag. | https://opencode.ai/docs/cli (Environment variables) | Same CLI page. | “`OPENCODE_PERMISSION` — Inlined json permissions config”. |
| `opencode acp --help` snapshot at v1.18.29 has no `--auto`. | https://raw.githubusercontent.com/anomalyco/opencode/v1.18.29/packages/opencode/test/cli/help/__snapshots__/help-snapshots.test.ts.snap | Tag `v1.18.29` (released 2026-09-04). | Snapshot `opencode acp --help`: options are help/version/logs/`--pure`/`--port`/`--hostname`/`--mdns`/`--mdns-domain`/`--cors`/`--cwd`. Contrast `opencode run --help`: “`--auto` auto-approve permissions that are not explicitly denied (dangerous!)”. |
| ACP CLI command source has no auto option (v1.18.29 and current `dev`). | https://github.com/anomalyco/opencode/blob/v1.18.29/packages/opencode/src/cli/cmd/acp.ts (SHA `da47d957…` at tag; same at `dev` `95daf906…`) | File last commit on `v1.18.29` path listing: 2026-06-08 (`c06ad7c8…`). | `builder`: `withNetworkOptions(yargs).option("cwd", …)` only. Command: `"start ACP (Agent Client Protocol) server"`. |
| `--auto` / `--yolo` / `--dangerously-skip-permissions` exist on TUI and `run`, not ACP. | https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/cli/cmd/tui.ts and `…/run.ts` (code search 2026-09-13) | `dev` as fetched; present at 1.18.29 help snapshot for `run`. | `.option("auto", { describe: "auto-approve permissions that are not explicitly denied (dangerous!)" })` in `tui.ts` and `run.ts`. Code search for `dangerously-skip-permissions` hits those files and `run-process.test.ts` only. |
| ACP `configOptions` builder exposes model / effort / mode, not auto. | https://github.com/anomalyco/opencode/blob/v1.18.29/packages/opencode/src/acp/config-option.ts (SHA `b730ae07…`) | Tag `v1.18.29`. Current `dev` (`ebf8baf1…`) still the same option ids. | `buildConfigOptions` returns `buildModelSelectOption` (`id: "model"`), optional `buildEffortSelectOption` (`id: "effort"`), optional `buildModeSelectOption` (`id: "mode"`). |
| ACP permission path forwards `session/request_permission` to the client (Allow once / Always allow / Reject); no skip-all in the handler. | https://github.com/anomalyco/opencode/blob/v1.18.29/packages/opencode/src/acp/permission.ts | Tag `v1.18.29`. | `permissionOptions`: Allow once, Always allow, Reject. If `connection.requestPermission` is missing, it `reply(…, "reject")`. |
| Feature request: expose per-session auto-approve via ACP `configOptions`; **not implemented** as of the issue. | https://github.com/anomalyco/opencode/issues/47918 | Opened **2026-09-08**; state **open**; updated 2026-09-08. | “Please expose reversible, per-session automatic approval (Yolo) through ACP `configOptions` and `session/set_config_option`… Tested the official Windows v1.18.29 binary… fresh sessions expose only `model` and `mode` (`build`/`plan`). Those modes switch successfully, but `auto`/`yolo` return `-32602`; no approval option is advertised.” |
| ACP protocol: agent **may** call `session/request_permission`; **clients** may auto-allow. | https://agentclientprotocol.com/protocol/tool-calls | Live protocol page; **no** revision date on page. | “The Agent **MAY** request permission from the user before executing a tool call by calling the `session/request_permission` method”. “Clients **MAY** automatically allow or reject permission requests according to the user settings.” |
| ACP `configOptions` can include a boolean “skip confirmation” option **if the agent advertises it**; OpenCode does not document doing so. | https://agentclientprotocol.com/protocol/session-config-options | Live; no page date. Example `brave_mode` is protocol illustration, not OpenCode. | Example option: `"id": "brave_mode", "name": "Brave Mode", "description": "Skip confirmation prompts and act autonomously"`. Categories listed: `mode`, `model`, `model_config`, `thought_level` — no reserved `auto` category. |
| v1.18.29 release notes do not add ACP auto-approve. | https://github.com/anomalyco/opencode/releases/tag/v1.18.29 | Released 2026-09-04. | Notes: Codex OAuth model filtering / gpt-6; no ACP permission flag. |

## Related (not equivalent)

- **`permission: "allow"` / granular `"allow"` rules** (https://opencode.ai/docs/permissions): documented as “run without approval”. That is static policy, not TUI `--auto` (which still enforces `"deny"` and only auto-answers `"ask"`). ACP docs never map this to skipping `session/request_permission`.
- **ACP “Always allow”** (`allow_always` on a single `session/request_permission`): documented in OpenCode ACP permission options and ACP spec; per-pattern/session remember, not skip-all.
- **Issue #28926** (closed): ACP “Always allow (all projects)” writing global config — not a skip-all flag.
- **Issue #48142** (open, 2026-09-09): `opencode attach` rejects `--auto` even though TUI has it — another surface missing `--auto`, not ACP.
- **Issue #48232** (open, 1.18.30 `dev`): ACP drops child-session permission requests; assumes client implements `requestPermission`.

## Could not verify

- Whether this machine’s `opencode acp --auto` / `opencode --auto acp` actually reject (vendor docs and source omit the flag; **this lookup did not execute the binary**). Repo-local claim that `opencode acp` rejects `--auto` is **not** vendor proof.
- Whether yargs would consume a **global** `--auto` before the `acp` subcommand; docs do not list `--auto` as global.
- Live HTML last-modified / CDN cache time for `opencode.ai/docs/*` (pages have no date).
- Whether `permission: "allow"` or `OPENCODE_PERMISSION` actually suppresses ACP `session/request_permission` on 1.18.29 (not stated on ACP docs; not measured).
- Whether any **newer than 1.18.29** release (e.g. 1.18.30 mentioned in #48232) added ACP `--auto` or a `configOptions` auto toggle. #47918 remains **open**; `dev` `config-option.ts` still has no `auto` id.
- Agent Client Protocol page revision dates (no date on fetched pages).
- Closed/merged PR that implements #47918: **not found** in the issues/PRs searched (`acp --auto`, `configOptions` auto/yolo). `github__search_pull_requests` for `acp auto configOptions yolo permission skip-all` in `anomalyco/opencode` returned **no items**.
- A vendor CHANGELOG file dedicated to ACP auto-approve: **not found**; v1.18.29 GitHub release notes do not mention it.
- Community/editor auto-approve settings (Zed/JetBrains) as OpenCode agent knobs: ACP spec says clients **MAY** auto-allow; OpenCode docs do not document a Zed/JetBrains skip-all arg for `opencode acp`.
