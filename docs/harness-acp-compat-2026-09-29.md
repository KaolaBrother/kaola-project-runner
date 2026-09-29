# Harness ACP compatibility — 2026-09-29 (desk digest, uncommitted)

Daily desk research, research-only mode. No live ACP smoke/E2E/UAT was run against any CLI, no
orchestrator Host was started, no pin, platform YAML, installer, or machine harness/skill was
changed, nothing committed or pushed, no packages installed. Every fact below is a read-only
network check (npm registry / `gh api`), a read-only local probe (`--version`, log/plist/config
reads, `diff`), or a repository read. Prior desks: `docs/harness-acp-compat-2026-09-25.md` and
`-2026-09-26.md` (the -09-24 one is referenced there). Untracked siblings of this file are left
untouched, including `kaola-workflow/archive/issue-216.discarded-*`.

## 0. Verdict

- **Class 3 (breaking, needs admission/coding): none.** Every surface a running seat uses today
  still exists and is pinned: the codex `acp_command` pins both `@openai/codex@0.156.1` and
  `@agentclientprotocol/codex-acp@1.13.1` (upstream's adapter 2.0.0 is not pulled by anything),
  the vendored Claude bridge is unchanged and its upstream is dormant, ACP v1 wire is unchanged,
  ZCode app-server is unchanged at 0.16.9.
- **Material class 2, top item: the codex pair moved to a major.** `@openai/codex` 0.158.0 went
  stable 2026-09-28 and `@agentclientprotocol/codex-acp` **2.0.0** (2026-09-28T14:11Z) requires
  `@openai/codex ^0.158.0`. Its breaking changes (AIR tool-call contract #530, ACP v1 conformance
  fixes #536, **"restore read-only mode and clarify access presets" #480**) touch exactly the
  read-only/access-preset semantics recorded in `platforms/codex.yaml` `acp_quirks`. Any adoption
  needs a live re-verification of that quirk text, not a bare record bump. Holding at 1.13.1
  remains coherent because the npx command bundles its own 0.156.1.
- **Material class 2, second item: the dsh watch fired.** npm `latest` for `@deepseek-ai/dsh`
  crossed from 0.1.5-rc.3 to **0.1.7-rc.2** (published 09-24; the dist-tag moved between the
  09-26 desk and today), and `next` now carries **0.2.0-rc.1** (09-28). The 09-25 watch rule —
  "when latest crosses to 0.1.6/0.1.7, re-read the dsh quirks (launcher version, ACP profile
  behavior)" — is triggered. Record bumps must not cross that line blind.
- **Material class 2, third item: record-lag batch.** kimi-cli 2.1.0→2.1.1 is still outstanding
  since 09-25 (not yet in `platforms/kimi-cli.yaml`); several platforms have moved on both
  machine and upstream (full table in §2). OpenCode stays 2.x-only (`@opencode/cli` 2.0.18);
  the 1.18 line (`opencode-ai` latest 1.18.33) is never a citation or recommendation source.
- **ZCode/ACP: no motion.** App 3.14.3 (build 7762), app-server 0.16.9 in today's startup log —
  both pins (cli=0.16.9, wrapper `80aa4e2`) exact. ACP spec repo activity since v1.9.1 is
  dependency bumps and docs/registry updates only; no stable v1 wire change (§4), so the
  `docs/acp-watch/` premise (stable v1 has no third tap / `session/attach`) still holds.

## 1. Consumer state (both repos, re-verified today)

- **KPR** `main` = `543b50d8` (2026-09-29 02:19 +0800), clean, 0 behind `origin/main`. Latest tag
  **v0.6.8** (tag object → content commit R = `82c0238e`). Since the 09-26 desk (then 27 commits
  past v0.6.2), four releases shipped: v0.6.3 (seat build/drain-restart, codex systemError turns,
  droid model verification), v0.6.4 (Delegator any-CLI Host #187, resumable Claude native id
  #186), v0.6.5 (named tiers #188, worker profiles/Opus medium #190, identity-proven force stop
  #191), v0.6.6, v0.6.7 (OpenCode default preset/sixth pool preset #200, skew-refusal recovery
  #198, Devin advertised-model fix #197), v0.6.8 (Host/Delegator heartbeat state #217, preset IDs
  #218, README cleanup #220, #221, #222 quota catalog fixes, #223 heartbeat authorization).
- **Grok Bot bridge pin cycle: v0.6.8 is fully pinned, and the tree is already mid-cycle for the
  next release.** Pin commit P = `6fa3cc6e` (2026-09-28 23:00 +0800) set `bridge.json`
  `saveable: true`, `accepted_commit = 82c0238e…`, `stage: pinned`, and the bridge's
  "Accepted revision" line to `82c0238e…` (release v0.6.8). Then `dfc77ac8` (#222, 09-29 01:09)
  changed the Delegator body hash and re-rendered the bridge back to `stage: content`,
  `saveable: false`, "Accepted revision: none yet" — the normal two-commit content/pin model
  reopening. Consequence: the **next** release needs a fresh pin commit before tag/publish
  (release gate in AGENTS.md / `docs/conventions.md`).
- **Installed skills vs accepted render: byte-identical, no desk/runner-start breakage.**
  `~/.zcode/skills` and `~/.agents/skills` both match the v0.6.8 render (`git archive v0.6.8
  skills`) file-for-file; the only extras are `.kaola-install-receipts` and KW-owned workflow
  skills (`kaola-workflow-*`, `workflow-*`). `kaola-delegator` exists only in `~/.agents/skills`
  (its designed destination) and matches v0.6.8. Installed roots date Sep 28 23:05–23:08, i.e.
  refreshed right after the v0.6.8 pin. The `skills/` (repo, at main) vs installed diff shows
  expected mid-cycle skew (main is 5 commits past the tag: #222, #223, archive sinks) — the
  #198/#215 owner-aware build-skew refresh routes own that path; no mismatch would block a desk
  or a runner `start` against the accepted v0.6.8 bytes.
- **KW** (`~/Workspace/kaola-workflow`): HEAD = `fe7e4443` = tag `kaola-workflow--v12.4.0`
  (2026-09-28), clean, 0 behind origin. Three releases since the 09-26 desk (v12.2.6 → v12.3.0 →
  v12.3.1 → v12.4.0). KW carries no CLI transport pins: `templates/agents/runtime-capabilities.json`
  has only two `version_floor` entries, both claude-code 2.1.277 AGENTS.md-reading documentation
  claims (machine claude 2.1.283 satisfies them); grok 1.0.40 now appears only in the historical
  decision record `docs/decisions/0019`; install scripts pin no npm versions. No KW-side drift.

## 2. Records vs machine vs upstream (probed 2026-09-29, read-only)

| platform | record (`acp_verified_versions`) | machine (`--version`) | upstream latest | drift |
|---|---|---|---|---|
| codex | cli=0.156.1; adapter=1.13.1 | 0.157.1 | cli **0.158.0** stable (09-28); adapter **2.0.0** (09-28, requires ^0.158.0) | **class 2 top** — paired major, see §3.1 |
| claude-code | cli=2.1.280; bridge=6c20f28 | 2.1.283 | npm 2.1.284 (09-28T17:11Z) | optional record; bridge upstream dormant |
| cursor-cli | cli=2026.09.18-9a7762b | **2026.09.26-dd393fe** | no public per-version feed | optional record (machine-observed) |
| devin | cli=3000.11.1 | 3000.11.3 | no public feed; local cache holds 3000.11.1 + 3000.11.3 | optional record (machine-observed) |
| droid | cli=0.225.1 | 0.228.0 | npm @factory/cli 0.228.0 (09-26) | optional record; machine = upstream |
| dsh | cli=0.1.5-rc.2 | 0.1.5-rc.3 | npm latest **0.1.7-rc.2**; next 0.2.0-rc.1 (09-28) | **class 2** — watch fired, see §3.2 |
| grok | cli=1.0.40 | 1.0.41 | 1.0.41 current (updater checked 09-28T18:35Z) | optional record; machine ahead |
| kimi-cli | cli=2.1.0 | **2.1.1** (was 2.0.2 on 09-26) | @moonshot-ai/kimi-code 2.1.1 (unchanged since 09-24) | **class 2** — outstanding record; machine now current |
| opencode | cli=2.0.15 (quirks measured on 2.0.11) | 2.0.18 | @opencode/cli 2.0.18 (2.x channel only) | optional record; 2.x moving fast (2.0.16→18 in 5 days) |
| zcode | cli=0.16.9; adapter=kaola-zcode-acp; wrapper 80aa4e2 | app 3.14.3 / server 0.16.9 (today's log) | zcode-acp repo at v0.50.0 (reference-only) | none on pins; reference drift is noise |

Machine freshness (Maya's calls, informational): since 09-26 the machine moved kimi 2.0.2→2.1.1,
claude →2.1.283, codex →0.157.1, cursor-agent →2026.09.26, droid →0.228.0, opencode →2.0.18.
Machine now behind upstream only on: claude 2.1.283 < 2.1.284, codex 0.157.1 < 0.158.0,
dsh 0.1.5-rc.3 < latest 0.1.7-rc.2. Everything else is at upstream current.

## 3. Upstream evidence per surface (what was checked, 2026-09-29)

### 3.1 Codex paired major — the day's material finding

- `openai/codex` `rust-v0.158.0` went **stable** 2026-09-28T05:07Z (0.159.0-alpha.13 is the
  forming pre-release line). npm `@openai/codex` latest = 0.158.0. 0.158.0 notes are TUI/MCP
  OAuth/WebSocket-auth/image-gen/sandbox fixes; nothing directly renames the app-server surface
  the adapter drives.
- `@agentclientprotocol/codex-acp` **2.0.0** (2026-09-28T14:11Z; repo
  `agentclientprotocol/codex-acp`; 1.13.2-preview.* never went stable) declares a dependency on
  `@openai/codex ^0.158.0`. Release notes: **BREAKING** "AIR tool call contract, exact diff
  patches, and fixes for every client" (#530); features `_meta.mcpStartupAwaitTimeoutMs` (#517);
  fixes "report authentication failures through ACP login flow" (#550), "resolve ACP v1
  conformance failures found by acp-tck" (#536), **"restore read-only mode and clarify access
  presets" (#480)**, and bundled codex updates through 0.158.0 (#549/#554/#559).
- Why this matters here: `platforms/codex.yaml` `acp_quirks` records that "ACP read-only is
  upstream on-request approval, not an OS sandbox; the Runner has no path to OS read-only" and
  maps the Runner's `--permission-mode` names onto upstream approval presets. #480 claims to
  *restore* read-only — if true, that quirk text and the mode mapping change under 2.0.0.
- Runner impact today: none. `acp_command` pins `--package @openai/codex@0.156.1 --package
  @agentclientprotocol/codex-acp@1.13.1`, so seats keep the verified pair. The record batch
  options are: (a) hold adapter at 1.13.1 and record machine-observed CLI 0.157.x (coherent; the
  npx command bundles 0.156.1 regardless of the machine binary), or (b) adopt the 0.158.0/2.0.0
  pair — which is **not record-only**; it needs a live re-verification of read-only/mode
  semantics (the #153 paired-bump pattern, plus a quirks rewrite). Recommendation for the next
  batch: (a) now, (b) behind a live desk when smoke is allowed.

### 3.2 dsh — the 09-25 watch item fired

npm `@deepseek-ai/dsh` dist-tags today: `latest 0.1.7-rc.2` (published 2026-09-24; the `latest`
tag moved off 0.1.5-rc.3 between the 09-26 desk and today), `next 0.2.0-rc.1` (2026-09-28),
`alpha 0.1.7-alpha.2`. The dsh quirks (launcher version behavior, ACP profile behavior) were
verified at 0.1.5-rc.2 (record) with the machine at 0.1.5-rc.3. A record bump to rc.3 remains
safe (same line); **crossing to the 0.1.7 line requires the quirks re-read the watch rule names**,
and 0.2.0-rc.1 is a forming minor — watch knowledge, not a candidate.

### 3.3 Other upstream checks

- **kimi-cli**: `moonshotai/kimi-code` latest still 2.1.1 (2026-09-24). The 09-25 record
  recommendation (2.1.0→2.1.1) is still outstanding in `platforms/kimi-cli.yaml` (last platform
  edit remains #153-era). The machine binary moved 2.0.2→2.1.1, closing the machine-behind-record
  gap; when the record batch lands, record and machine will agree at 2.1.1.
- **claude-code**: npm 2.1.284 (2026-09-28T17:11Z); machine 2.1.283; record 2.1.280. Cadence is
  roughly daily patch releases; nothing in the 2.1.28x notes names the stream-json input channel,
  `--resume`, or ACP-adjacent behavior the vendored bridge depends on (bundled
  `@agentclientprotocol/sdk` 0.16.1 is deliberately decoupled from the SDK's own 1.5.x line —
  noise for this fork).
- **opencode**: 2.x channel only (`@opencode/cli`): 2.0.16 (09-24), 2.0.17, 2.0.18 = npm latest
  and machine. The record is 2.0.15 and the recorded quirks (no skip-all on 2.0.11; V2 loopback
  HTTP + the child-env NO_PROXY append) were measured on 2.0.11 — the fastest-moving 2.x surface
  we track; when the record batch lands, re-check the loopback/proxy behavior on the recorded
  version. The 1.18 line (`opencode-ai` latest 1.18.33, 09-21+) remains deliberately uncited;
  the `anomalyco/opencode` GitHub tag feed currently surfaces only vscode-* tags, so npm remains
  the 2.x channel truth. (Desk-brief note: the brief named 2.0.11 as the `acp_verified_versions`
  baseline; the actual record value is 2.0.15, with 2.0.11 being the quirks-measurement version.
  Both tracked above; no 1.18.x bump is recommended anywhere.)
- **grok**: upstream `xai-org/grok-build` still exposes no tags/releases bodies; machine updater
  `~/.grok/version.json` (checked 2026-09-28T18:35Z) says 1.0.41 current, `stable_version` null.
  Top `~/.grok/CHANGELOG.json` entries (sports_search tool, subagent fullscreen fix, agent
  frontmatter mcpServers fix, Ctrl+P) all `breaking_change: false`. Record 1.0.40→1.0.41 stays an
  optional batch item; KW's 1.0.40 references are historical decision text only.
- **droid**: `@factory/cli` 0.228.0 (2026-09-26) = machine; record 0.225.1. No public
  release-notes feed (GitHub exposes no releases; changelog 404) — ACP relevance of 0.226–0.228
  unverified, so any bump stays record-only/optional, native-ACP surface pinned at 0.225.1.
- **devin / cursor-cli**: self-managed caches; devin machine 3000.11.3 (record 3000.11.1);
  cursor-agent machine 2026.09.26-dd393fe (record 2026.09.18-9a7762b). No public per-version
  feed for either; both are machine-observed optional records.
- **Vendored Claude bridge**: upstream `harukitosa/claude-code-acp` HEAD is still the pinned
  commit `6c20f28` (2026-03-18) — zero commits since the pin, repo dormant. No drift. The npm
  package `claude-code-acp` remains a different, older project (never referenced).

## 4. ZCode / ACP protocol surfaces

- **ZCode**: `/Applications/ZCode.app` 3.14.3 (CFBundleVersion 3.14.3.7762); today's
  `~/.zcode/cli/log/zcode-2026-09-29.jsonl` startup events carry `context.version: "0.16.9"`.
  Pins `cli=0.16.9` and wrapper `80aa4e2` exact; no drift. The release feed
  (`cdn-zcode.z.ai/.../latest-mac.yml`) was not re-probed today; it has answered 404 from this
  network all week and nothing pins to it.
- **zcode-acp reference** (`william0wang/zcode-acp`, never vendored, protocol reference only):
  v0.48.0 (09-25, workflow-gate subsystem) → v0.49.1, v0.49.2 (09-28) → **v0.50.0 (2026-09-28,
  serve the web client same-origin from the hub via remote.webDir)** — three releases in one day,
  all remote/hub/web-facing; none touch the compact busy-window or `usage_update` semantics the
  Runner's own `kaola-zcode-acp.py` recorded from 0.47.x. Watch knowledge only; no action.
- **ACP spec** (`zed-industries/agent-client-protocol`): no releases since v1.9.1 / schema-v1.23.0
  (2026-09-18); commits since are dependabot bumps and registry/docs updates. The unstable
  channel items (v1 session notice, v2 prompt-insertion ID, request-scoped MCP-over-ACP) remain
  unstable — off the Kaola transport path; all ten platforms stay `protocol=1`. The
  `docs/acp-watch/` frozen design's premise (stable v1 has no third-party stdio tap / no
  `session/attach`) still holds. TS SDK `@agentclientprotocol/sdk` 1.5.1 (from 1.5.0) is
  SDK-housekeeping, not a wire change.

## 5. Classification summary

- **Class 3 (breaking / must act): none.**
- **Material class 2:**
  1. Codex paired major available (cli 0.158.0 stable + adapter 2.0.0, hard-coupled). Adoption
     changes documented read-only/mode quirks (#480) and the tool-call/diff contract (#530);
     decide hold-at-1.13.1 (record-only CLI observation) vs live-verified adoption. No running
     seat is affected today.
  2. dsh `latest` crossed to 0.1.7-rc.2 (watch fired) and 0.2.0-rc.1 formed on `next`; the
     0.1.7 line needs a quirks re-read before any record names it.
  3. Record-lag batch (one #153-style batch): kimi-cli 2.1.0→2.1.1 (outstanding, now
     machine-matched), grok 1.0.40→1.0.41, dsh rc.2→rc.3, opencode 2.0.15→2.0.18
     (2.x only), claude-code 2.1.280→2.1.283/2.1.284, droid 0.225.1→0.228.0, devin
     3000.11.1→3000.11.3 and cursor-cli 2026.09.18→2026.09.26 (machine-observed), codex cli
     record decision per item 1.
  4. Bridge bookkeeping: grok-bot bridge is at content stage mid-cycle; the next release must
     complete a fresh pin (P naming R at the tag) per the release gate.
- **Class 1 (noise):** ACP spec deps/docs motion; zcode-acp v0.49/v0.50 remote-web features
  (reference-only); vendored-bridge upstream dormancy (unchanged); ZCode app/server constants;
  KW v12.3/v12.4 with no CLI transport pins; grok 1.0.41 non-breaking changelog; kimi 2.1.1
  unchanged; SDK 1.5.1; installed-vs-main skills skew covered by existing owner-aware refresh
  routes.

## 6. Watch list for the next desk

1. Codex-acp 2.x: if a live window opens, re-verify read-only/mode mapping (#480), AIR contract
   (#530), conformance (#536) on the 0.158.0/2.0.0 pair; otherwise hold at 1.13.1 and record
   machine-observed CLI only. Also watch for a 1.13.2 stable backport line.
2. dsh: any 0.1.7 record candidate requires the launcher/ACP-profile quirks re-read; 0.2.0-rc.1
   forming on `next`.
3. opencode 2.x cadence (three minors in five days): re-check the loopback-HTTP/NO_PROXY quirk on
   whatever version the record batch names; never 1.18.x.
4. grok-bot bridge: next release's fresh pin cycle (content stage is open now).
5. zcode-acp release velocity (three in one day) — still reference-only; re-check only if a
   release touches session/handlers/extensions rather than remote/web.
6. ZCode app update >3.14.3 with a changed app-server version (pin `cli=0.16.9` would move);
   claude-code patch cadence (2.1.284 already out).

## 7. Evidence trail

Local (read-only): `git log/tag/fetch/status` both repos; `platforms/*.yaml` pins;
`git show` on tags v0.6.3–v0.6.8, pin commit `6fa3cc6e`, `dfc77ac8`; `git archive v0.6.8 skills`
+ `diff -rq` against `~/.zcode/skills` and `~/.agents/skills`; `--version` for nine CLIs;
ZCode `Info.plist` via `defaults read` + `~/.zcode/cli/log/zcode-2026-09-29.jsonl` version
events; `~/.grok/version.json` + `CHANGELOG.json`; `vendor/claude-code-acp/UPSTREAM.md`; KW
`runtime-capabilities.json` / `runtime-contract-adapters.json` / decision 0019 greps.
Network (read-only): `gh api` on `openai/codex` (releases + 0.158.0 body),
`agentclientprotocol/codex-acp` (releases + v2.0.0 body), `william0wang/zcode-acp` (releases +
v0.50.0 body), `zed-industries/agent-client-protocol` (releases + commits),
`moonshotai/kimi-code`, `anomalyco/opencode` (tags), `xai-org/grok-build` (tags, none),
`harukitosa/claude-code-acp` (commits); `npm view` on `@anthropic-ai/claude-code`,
`@openai/codex`, `@agentclientprotocol/codex-acp` (version/repository/time/deps),
`@factory/cli`, `@moonshot-ai/kimi-code`, `@opencode/cli`, `opencode-ai` (dist-tags only,
1.18 line deliberately uncited), `@deepseek-ai/dsh` (dist-tags + time),
`@agentclientprotocol/sdk`.

Not verified today (no live smoke allowed): any live ACP run; codex-acp 2.0.0 behavior
(read-only/mode/AIR); dsh 0.1.7 launcher/ACP-profile behavior; opencode 2.0.16–2.0.18
loopback/proxy behavior; droid 0.226–0.228 ACP behavior; kimi 2.1.1 ACP behavior; the ZCode
update-feed manifest. All record bumps named above stay record-only until a live run says
otherwise.
