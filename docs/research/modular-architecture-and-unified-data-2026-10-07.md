# KPR modular architecture & KPR+KW unified data research — 2026-10-07

Bounded read-only research, issue #270. Owner sources: dot relay `Sentinel_74387efc93448191b2cd28b832892096` + scope additions `Sentinel_08d1c37b…`, `Sentinel_0ff6b5eb…`, `Sentinel_36362916…`; identity correction (holder 78d503e2, retired 09cfe105) and KW-README-drift finding received from dot/bridge mid-research. **Host compiles sources; dot MAIN personally owns analysis; Fable review only after dot.** No implementation; KW repository treated read-only; no grant/authorization content is copied into this document.

## 1. Identity inventory (Deliverable A)

| Name (owner) | Resolved identity (evidence) | Status |
|---|---|---|
| KPR | this repo, `KaolaBrother/kaola-project-runner`, v0.9.1 @ `3de9f61a`+pin `1112070e` | certain (self) |
| KW / KWL | **Kaola-Workflow**, `KaolaBrother/Kaola-Workflow` ("Pairs with Kaola Project Runner…", pushed 2026-10-05; `LICENSE` file = MIT although GitHub shows "no license" — detection quirk, both facts recorded); local read-only checkout `~/Workspace/kaola-workflow`; "KWL" itself unexpanded (L = loader/library/link unverified) | KW verified; KWL expansion unknown |
| Py | **Pi** — `badlogic/pi-mono` live-redirects to **`earendil-works/pi`** (bridge live check + my fetch: MIT, ~6,796 commits, very active; packages table: `chord`, `pi-durable`, `pi-telemetry`, `pi-ai`, `pi-agent-core`, `pi-coding-agent`, `pi-tui`) | strong; "Py" spelling itself unconfirmed |
| Pass.io | **Paseo** — `getpaseo/paseo`, [paseo.sh](https://paseo.sh/) (self-hosted daemon for Claude Code/Codex/Copilot/OpenCode/Pi; project→workspace→session; TypeScript plugins from npm/git/local) | strong; "pass.io" spelling unconfirmed |
| Worker | **Cloudflare Workers / Workflows** — durable execution engine on Workers; 2026 additions: fibers (`runFiber`/`startFiber`, DO-eviction survival), Dynamic Workflows (MIT lib) | plausible; not owner-confirmed |
| T3 | **T3 Code** — `pingdotgg/t3code`, "the open-source control plane for coding agents" (web GUI for Codex/Claude/OpenCode; MIT; ~23.3k stars) | plausible; residual ambiguity (T3 stack) — "Worker and T3 may denote different projects" holds |
| DSH | **DeepSeek Harness** — located through actual KPR integration: `platforms/dsh.yaml` + `scripts/adapters/dsh.sh` + `scripts/kaola-dsh-acp.py` (+ `kaola-dsh-steer.mjs`) | certain (in-tree) |

Adjacent representatives (durable-execution category, for comparison only): **Temporal** (core MIT, company-stewarded, not CNCF), **Restate** (SDKs MIT, runtime BSL, VC-funded). Verification status: live web checks 2026-10-07; stats quoted from the live pages at fetch time; not independently re-audited.

**Concrete version-dependency/contract-reuse example (dot's finding, validated)**: KW `README.md:88` says "Send instructions via ACP **or PTY**" and `README.md:104` says "Runner currently provides **seven target CLI Skills**", while current KPR contract is **ten platforms, ACP-only, PTY retired (#130)** (`AGENTS.md:13`, `docs/architecture.md`). Marked as **documentation drift** in KW's synergy section; neither README copied as fact; KW not modified. This is exactly the cross-repo version coupling a shared contract registry would surface mechanically.

## 2. Four-layer mapping (dot's frame) — existing capability vs true fragmentation vs governance gap

### L1 — OS process hosting
Existing (source-evidenced): per-session carrier `runtime-tmux.sh`; **launchd is one narrow optional backend, not the hosting model** — `scripts/kaola-launchd-broker.py` (#266) exists solely so a holder survives its desktop-app caller: one-shot per-user job, child spawned `start_new_session`, re-parented to the service manager, fixed env allowlist (`PASS_ALWAYS/PASS_PROXY/PASS_KAOLA`); `--launch-backend {direct,launchd,auto,systemd-user}` is already a pluggable flag. Fragmentation: `systemd-user` unverified on Linux; no supervision/restart-policy abstraction (health/backoff/reclaim are in the holder+Host layer instead); cross-platform story is macOS-first.

### L2 — ACP protocol adapters
Existing: ten capability manifests `platforms/*.yaml` (models/tiers/effort/native-steer/`acp_mode_config_id` — already a capability-declaration format), ten `scripts/adapters/*.sh`, per-platform bridges (`kaola-zcode-acp.py`, `kaola-opencode-acp.py`, `kaola-dsh-acp.py`) + shared holder `kaola-acp-holder.py` (advertises `holder_features`), vendored `claude-code-acp` derivation with documented upstream. Fragmentation: capability *data* (yaml), *behavior* (adapters), and *bridges* evolve on separate cadences; steering adaptations are per-platform code, only partially summarized back into manifests.

### L3 — data contracts
Existing: typed, versioned schemas with allowlists and single-writer rules — `kaola-heartbeat-prompt/2`, `kaola-delegator-heartbeat/1`, `kaola-dispatch-index/1` (`scripts/kaola-record-contract.py`); KW side: `workflow-state.md`, mission ledger (`n/name/details/status`), `finalization-summary.md` heading contract, `chain-receipt.json` (codeTreeHash), `.cache/final-validation.md` (column-0), governed by KW's JS (`kaola-workflow-adaptive-schema.js`). **True fragmentation: two implementations (Python + JS) police neighboring contracts across the two repos, with no shared registry or conformance suite** — the README drift above and the #267-era semantics churn are concrete divergence evidence.

### L4 — module assembly
Existing: render pipeline (`render-skills.py --write/--check`, `templates/budgets.json` progressive-disclosure budgets, generated-output-never-hand-edited), selective install (`install-local.sh --platform … --runtime|--skills-dir --method link|copy --no-orchestrator --bin-links`), the grok-bot two-commit content/pin release model, optional-KW posture (Workflow "on if available"). Fragmentation: composition is **install-time only** — no runtime on-demand module loading/activation; optional components are script flags rather than declared modules with dependency closure.

### The governance gap — Agent free file writing (owner-named; evidenced, not assumed)
Free prose files are still the cross-agent evidence layer: this project's own record shows the class — CAD delivery-log authorization narration recurrence (#269), uncommitted authoring residue in 267/268 worktrees (needed record commits), scattered `.cache`/`/tmp` receipts (a whole exit-receipt reconstruction episode), and CAD's evidence-gap classes (prose-only done duties). Typed single-writer records exist only for the three KPR schemas + KW's artifacts; everything else is ungoverned free files with no ownership, query, or integrity contract. That is the actual gap a unified data layer must close — not the heartbeat (already typed) and not launchd.

## 3. KPR+KW unified data management (mapping; responsibilities preserved)

- **Identity links today**: repo/project-code → issue → run (`workflow-state.md`) → missions (ledger) → sessions (Runner receipts) → dispatch items (index) → artifacts — each hop exists, but in different files, formats, owners, and repos; nothing joins them (the #267 item↔task binding lesson; sink's own issue-number set capture is the closest join point).
- **Ownership/single-write**: per-artifact single-writer is already strong (heartbeat: host+bound sideagent only; delegator file: outer/bridge; workflow-state/ledger/sink: KW; Runner receipts: tools). Gap: **no cross-artifact transaction or idempotent multi-file update** (heartbeat+index+delegator move in three writes; crash windows observed: my transient `state-missing` during a node checkpoint replace).
- **Active state vs Git evidence**: current-only JSON (heartbeat, delegator) vs Git-committed archives/finalization summaries — the #259/#260 closeout proved this works when disciplined; free prose (delivery logs) escapes both.
- **Concurrency/atomicity/recovery**: `StateLock` per file; KW sink idempotent receipts + resumable transactions; no cross-file atomicity; recovery relies on per-tool receipts.
- **Install vs project data**: skill roots (`~/.zcode/skills`, …) vs consuming-project `.kaola/` + `kaola-workflow/` — documented boundary; installed-vs-repo drift is real (measured: KW claim.js `4b02b82f`→`bf841bec` episode) and undetected by any tool today.
- **Permissions/secrets**: launcher env allowlist; no secret store; receipts embed absolute paths verbatim (KW `--keep-output` documents the leak class).
- **Duplicate/missing detection**: exists but artifact-specific (KW closure-audit drift detector; KPR validate lane-integrity; state `unknown_paths`). No general missing-record/duplicate-copy detector over the file set.
- **Version migration/portability**: `state migrate` v1→v2, delegator migrate, pin model — good per-artifact; **no cross-repo contract-version negotiation** (README drift example).
- **KW ownership boundaries to preserve** (owner requirement): claims/worktrees/mission ledger/validation/finalize/sink stay distinct from Runner communication and Host judgment; Git delivery facts remain authoritative.

### Storage options compared (no preselection — decision is dot's)
1. **Files + unified access layer** (one library/API implementing the identity spine, queries, and integrity checks over today's artifacts): preserves Git-evidence principle and single-writer rules; lowest migration cost; weakest transactions.
2. **Embedded DB** (e.g., SQLite-class): real transactions/queries; but bypasses the Git-evidence principle unless paired with exports, and adds backup/secret/versioning story.
3. **Service storage** (daemon; Paseo/Temporal-style): strongest consistency and remote access; conflicts with local-first + the owner's explicit no-resident-loop boundary; largest operational change.

### Contract inheritance (Sentinel_36362916 requirement)
Composable optional modules must **inherit one rule set, not copy their own**. Closest existing open-source embodiment: **Pi's package split** — `chord` ("standalone application-composition runtime for services, replicated state, RPC, and plugins"), `pi-durable` (durable conversation/task/document runtime), `pi-telemetry` ("vendor-neutral telemetry **contracts**, reference adapter, **conformance tests**, typed schemas") — i.e., contracts + conformance + durable runtime as separately adoptable packages under one version scheme. That is the design pattern (not necessarily the dependency) for KPR+KW: a **contract registry with generated validators + conformance suites** consumed by both repos, replacing the dual Python/JS implementations.

## 4. Fitting alternatives — with explicit reasons-against (Deliverable B)

| Candidate | What genuinely fits | Reasons-against |
|---|---|---|
| **Paseo** (`getpaseo/paseo`) | self-hosted daemon control plane; provider-wrapping of existing CLIs; plugin system (npm/git/local); remote/local split | resident daemon vs owner's no-resident-loop; replaces rather than composes KPR's per-session ACP holder; TS-plugin trust model vs KPR's permission boundaries |
| **Pi** (`earendil-works/pi`: chord/durable/telemetry) | the best live reference for inheritable contracts + conformance + durable data + composition-with-plugins | adoption as a dependency pulls a TS ecosystem into a bash/python project; library-level reuse ≠ protocol-level; owner has not confirmed Pi is the intended "Py" |
| **Cloudflare Workflows/Workers** | durable execution, fibers, dynamic composition | cloud/V8-isolate bound; not local-first; vendor runtime |
| **Temporal** | canonical durable workflow | server dependency + operational weight; workflow-as-code paradigm sits awkwardly with Git-evidence lifecycle |
| **Restate** | lighter durable runtime | runtime is BSL; resident service; same paradigm mismatch |
| **T3 Code** (`pingdotgg/t3code`) | polished agent control-plane UX | GUI control plane, not headless data/contract reuse; no contract-inheritance value |

## 5. Minimal viable architecture + incremental migration (proposal for dot's analysis — not a decision)

- **M1 — contract registry + conformance**: one versioned contract source for the shared artifacts (three KPR schemas + KW's five), generating validators for both Python and JS sides; kills the dual-implementation divergence (README drift becomes a mechanical check).
- **M2 — identity spine over files (option 1 storage)**: canonical ID scheme (project/run/task/session/dispatch/artifact) + one access-layer API joining existing files; missing-record/duplicate-copy detection becomes generic; no storage migration.
- **M3 — module manifests with dependency closure + degradation**: declare optional modules (KW, launcher backends, delegator, orchestrator) with capabilities, contract versions consumed, and defined behavior when absent (KPR-without-KW already degrades gracefully; make it declared rather than implicit).
- **M4 — evidence discipline for free files**: typed receipt contract for the delivery-log/report class (the #269 lesson generalized), keeping prose for humans and locators for machines.
- Each step independently shippable; no ACP change; preserves progressive disclosure, the pin model, single-writer rules, and KW's lifecycle ownership. No big-bang rewrite.

## 6. Uncertainty register

- Owner-name resolutions (Py/Pi, Pass.io/Paseo, Worker, T3) are evidence-strong but not owner-confirmed; identity table is the disambiguation instrument.
- KW "KWL" expansion unknown; KW README drift could be stale-doc-only — treat as version-coupling symptom, not intent.
- Web facts (stars/commits/licenses/push dates) are live-page reads on 2026-10-07; Temporal/Restate licensing summarized from official/launch sources, not legal review.
- Scattered-file incidents cited are this workspace's own evidenced cases (issue #269, archived run records); no claim of incidence elsewhere.
