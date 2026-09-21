# OpenCode V2 ACP — upstream research (Mission 1)

Researched 2026-09-21. Upstream tracker is **`anomalyco/opencode`** (not `opencode-ai/opencode`,
not `sst/opencode`). All issue numbers below are that repo unless stated.

## R1 — ACP is NOT ported to V2 yet (decisive)

**#35457 "Port ACP support to V2 core and APIs" — OPEN, priority "Low".** Body (verbatim points):

- "ACP exists on the v2 branch, but it has not been ported to the V2 core/API stack end-to-end."
- "`packages/opencode/src/acp/service.ts` still uses `@opencode-ai/sdk/v2` and calls the
  compatibility `sdk.session.*` APIs." Those routes "are still backed by the legacy app services
  such as `SessionPrompt`, `Session`, and the legacy event/permission bridge."
- Unmet acceptance criteria include: "`opencode acp` creates and drives V2 sessions end-to-end."
- "Track this after the remaining V2 API work needed for session lifecycle, command execution, MCP,
  permissions/events, and generated clients is stable."

So on the V2 line, `opencode acp` is a **legacy-compat shim over a V2 server**, not a ported
transport. The session-scoped failure on 2.0.11 is an upstream-acknowledged incompleteness with no
fix version and an explicitly deprioritised port — not a local environment fault.

Corroborating: `https://opencode.ai/v2/docs/acp` returns **404** (the V1 page
`https://opencode.ai/docs/acp/` exists and documents `opencode acp` with no flags). The V2 doc index
has no ACP section. GitHub Releases has **no v2 release entries at all** — v2.0.10 / v2.0.11 exist
only as tags, while **v1.18.31 is still marked "Latest"**.

## R2 — V2 `serve` auth is always-on; 401 is by design

- **#49452 (OPEN, 2026-09-17) "v2.0.5: opencode serve returns 401 when server auth env vars are
  unset or empty."** A loopback-only server returns 401 even with `OPENCODE_SERVER_PASSWORD` and
  `OPENCODE_SERVER_USERNAME` absent or empty; the server logs an auto-generated password. No opt-out.
- **#45856 (OPEN) "v2 serve: configured Basic Auth credentials always return 401."**
- **#31254 (CLOSED) "opencode serve requires HTTP auth, breaking SDK / third-party clients."**
- **#44640 (OPEN) "Harden server mode: require auth for non-loopback binds (secure-by-default)"** —
  i.e. loopback-always-auth is itself contested upstream.

=> The issue-112 observation "child listens on loopback and rejects unauthenticated requests with
401" is **expected V2 behaviour**, not the defect. The defect, if any, is whether the ACP bridge
knows its child's generated password. Upstream has no ticket naming that exact link, so it stays a
*hypothesis*, subordinate to R1 which already explains a uniform session-method failure.

## R3 — ACP `session/new` on 2.0.x has a second, independently confirmed regression

**#50236 (OPEN) "acp: session/new catalog ignores config providers, agents, and default model since
2.0.4."** Broken on **2.0.4, 2.0.6, 2.0.11**; working on **2.0.3**. Cause: "refactor(protocol):
remove plugin activation wait" replaced `client.plugin.awaitActivation()` in `loadCatalog()` with a
5 s poll that exits on the first enabled model, and "refactor(core): split provider and model
registries" gated provider visibility on `activation === "enabled"`. No maintainer response, no fix
version, no workaround. Directly names our exact CLI version.

## R4 — prior art for this exact symptom (V1 era, all closed, none matching our env)

| # | state | root cause | applies here? |
|---|---|---|---|
| #31091 | closed (stale-bot) | ACP `session/new` -> "Internal error: OpenCode service failure", `data.service="directory"`; 5 parallel SDK calls in `loadDirectorySnapshot()` | same shape, different `data` payload (ours: `errorName: "ClientError"`) |
| #31096 | closed | fix(acp): bypass HTTP proxy for localhost SDK client requests | **must rule out locally** — a set `http_proxy`/`HTTP_PROXY` makes the bridge's localhost HTTP client fail |
| #31076 | closed | `Context.empty()` -> "No models available" | fixed pre-2.0 |
| #17285 | closed | Windows; comment locates real cause in `~/.local/share/opencode/logs/*.log` | **gives the probe**: the swallowed cause is logged |
| #25568 | closed (stale) | macOS, 1.14.x, `-32603` `data:{}` | unresolved |

Two actionable probes fall out: (a) check `http_proxy`/`HTTPS_PROXY`/`NO_PROXY` in the live env;
(b) read `~/.local/share/opencode/logs/*.log` (and `opencode acp --print-logs` / `--log-level DEBUG`,
which #31091 shows are accepted globals) to recover the cause `fromUnknownError()` swallows.

## R5 — the wedged managed service is a known open upstream defect

**#41696 (OPEN) "opencode2 became stuck starting its managed background server"** — macOS/arm64,
**same port 49374**, same "Timed out waiting for the background service to start", same silent
repeated `serve --service` respawn. Upstream remediation is
`opencode service set port <port>` then restart. #41793 improved error surfacing; a later comment
reports the wedge still reachable via "contender overlap" in `Service.ensure`/`recognizeIncumbent`.
Related: #49009 (closed, "background service startup reports generic timeout, hiding port-in-use
root cause"), #35158 (tracking).

=> This is an upstream product defect with an upstream remedy that **mutates user config**. It is
out of Runner scope; record it, do not build a classifier or retry layer around it (project contract
names that as overengineering evidence).

## R6 — V2 config migration (official)

`https://opencode.ai/v2/docs/migrate-v1` covers config only, and confirms one fact the Runner
depends on: **"`variant` joins model reference after `#`"**, e.g. `"anthropic/claude-sonnet-4-5#high"`.
Other renames: `permission` -> ordered `permissions` array (`bash`->`shell`, `task`->`subagent`,
`write`/`patch`->`edit`), `agent`->`agents`, `prompt`->`system`, `disable`->`disabled`,
`provider`->`providers` (`npm`->`package`, `aisdk:` prefix), `mcp.servers`, `command`->`commands`,
`plugin`->`plugins`, `autoshare`->`share`. The guide says **nothing** about CLI flags, ACP, the
service, or server auth.

=> The Runner's `OPENCODE_CONFIG_CONTENT` payload in `adapter_prepare_model_environment` is written
in V1 config shape and must be re-verified against these renames.

## R7 — `--mini` in V2

- **#41513 (OPEN)** "`opencode run --interactive/-i` is a no-op: interactive mode only activates via
  **hidden** `--mini`" — `--mini` was a *hidden* flag in the V1 line.
- **#49617 (OPEN, created after 2026-08-01)** "[FEATURE]: Add session switching to `opencode --mini`"
  still writes it as a top-level flag.
- **#49764 / #49807 (OPEN)** concern `opencode2` invoked-bin naming in the mini exit hint.

=> Help output not listing `--mini` is **not** proof it is rejected; hidden flags do not print.
Whether V2 accepts `--mini` must be settled by executing it, not by reading `--help`. (Issue #112
already records `opencode /some/dir --mini --auto` exiting 1 — to be re-confirmed live, and the
distinct failing token identified.)

## Unknowns after research

- No upstream ticket names the exact 2.0.11 ACP `errorName: "ClientError"` on every session method.
  R1 explains it structurally; R2/R3 are contributing candidates. No fix version exists for any of them.
- Whether `opencode auth login` clears it: untested upstream and **out of bounds here** (mutates user
  credentials).
- V2 `mini` TUI chrome strings: not documented anywhere; must be captured live.
