# KPR modular architecture & KPR+KW unified data research — 2026-10-07 (DRAFT v2, bridge-readback corrected)

**Status: first-draft Host research/suggestions. dot MAIN independently owns analysis; Fable collaborative review follows dot — neither this document nor its publication is acceptance.** Issue #270. Owner sources: dot relay `Sentinel_74387efc93448191b2cd28b832892096` + additions `Sentinel_08d1c37b…`, `Sentinel_0ff6b5eb…`, `Sentinel_36362916…`, bridge readback of draft v1 (`9acaecbe`), identity correction (current holder `78d503e2`, `09cfe105` retired). Read-only: no implementation, no installs, KW repository untouched, no grant/authorization content copied here. v1→v2 changes: every architecture claim now carries a source locator or is narrowed/marked unverified; daemon tradeoffs restated fairly (the owner's no-resident rule governs the KPR Host, not a blanket architecture prohibition); existing mechanisms (locks, atomic replace, dispatch↔task links, restart tooling, install-time verification) recognized; M1–M4 demoted to candidate options.

## 1. Identity inventory (Deliverable A) — evidence per row, fetched 2026-10-07

| Name | Identity | Evidence (checked) | License | Maintenance snapshot | Uncertainty |
|---|---|---|---|---|---|
| KPR | this repo | v0.9.1 tag `3de9f61a`, pin `1112070e`; `AGENTS.md` Architecture line | in-repo | released 2026-10-07 | — |
| KW | [KaolaBrother/Kaola-Workflow](https://github.com/KaolaBrother/Kaola-Workflow) | repo description pairs with KPR; local checkout `~/Workspace/kaola-workflow` | `LICENSE` file **MIT** (GitHub's "no license" display is a detection quirk — both facts recorded) | pushed 2026-10-05 | "KWL" expansion unverified |
| Py→Pi | [`earendil-works/pi`](https://github.com/earendil-works/pi) (live redirect from `badlogic/pi-mono`, checked twice) | packages/ actually contains `chord`, `telemetry`, `ai`, `durable`, `agent`, `coding-agent`, `tui` (README table + repo tree); 6,796 commits | MIT (repo page) | very active (fetch-day stats) | **chord/durable internals not yet source-inspected** — README table ≠ behavior proof; "Py" spelling unconfirmed |
| Pass.io→Paseo | [`getpaseo/paseo`](https://github.com/getpaseo/paseo), [paseo.sh](https://paseo.sh/) | real layout: `packages/server` ("Paseo daemon — agent process orchestration, WebSocket API, MCP server"), `plugins/` + `plugin-examples/`, `packages/{app,desktop,cli}`; 5,735 commits | **Apache-2.0** (`LICENSE`) | active (fetch-day) | "pass.io" spelling unconfirmed |
| T3 | [`pingdotgg/t3code`](https://github.com/pingdotgg/t3code) | "open-source control plane for coding agents" (web GUI; Codex/Claude/OpenCode) | MIT (search-verified; not file-checked) | ~23.3k stars, young project | layout not inspected; T3-stack ambiguity remains |
| Worker | [Cloudflare Workflows](https://developers.cloudflare.com/workflows/) / Workers | durable execution on Workers; 2026: fibers (`runFiber`/`startFiber`), Dynamic Workflows (MIT lib) | platform + MIT lib | GA since 2025-04, active | owner intent unconfirmed |
| DSH | **DeepSeek Harness**: launcher binary `dsh` (0.1.7-rc.2, `DSH_BIN`); ACP harness = npm **`@deepseek-ai/dsh-acp-app`** + **`@deepseek-ai/dsh-acp`**, version-pinned by the launcher (no standalone harness upgrade); `agentInfo deepseek-harness-acp/0.0.1` | via KPR's actual integration: `platforms/dsh.yaml:9,27,29` + `scripts/adapters/dsh.sh` + `scripts/kaola-dsh-acp.py` + [`docs/api.md#dsh-loaded-acp-harness`](https://github.com/KaolaBrother/kaola-project-runner/blob/main/docs/api.md#dsh-loaded-acp-harness) | npm @deepseek-ai scope | 0.1.7-rc.2 verified in-repo | official repo URL not separately fetched (package names are the verified identifiers) |
| adjacent | Temporal (core MIT, company-stewarded, not CNCF — search-verified), Restate (SDKs MIT, runtime BSL) | official sites temporal.io / restate.dev + launch sources | as stated | active, VC-funded | not file-checked this pass |
| protocol family | **ACP itself** — [zed-industries/agent-client-protocol](https://github.com/zed-industries/agent-client-protocol): the open protocol KPR already rides; versioned spec + conformance-minded design — distinct coverage as the in-house L2's own upstream | named as family representative | — | — | not re-verified this pass (KPR contract knowledge) |

No count padding: each row either is owner-named, KPR-integrated, or covers a distinct family (daemon control plane, composable runtime+contracts, durable execution cloud/infra, agent protocol).

**Concrete version-dependency example (validated)**: KW `README.md:88` "Send instructions via ACP **or PTY**" and `:104` "Runner currently provides **seven target CLI Skills**" vs KPR current contract (ten platforms, ACP-only, PTY retired #130; `AGENTS.md:13`). Marked documentation drift; neither README copied as fact; KW unmodified. (What it proves: cross-repo docs can silently diverge from a shipped contract. It does **not** by itself prove a shared validator registry is required — see §5 options.)

## 2. Four layers — existing capability (with source), verified-absent gaps, and the governance gap

### L1 — OS process hosting
Existing: per-session carrier `runtime-tmux.sh`; pluggable `--launch-backend {direct,launchd,auto,systemd-user}`; `scripts/kaola-launchd-broker.py` (#266) for the narrow outside-caller-survival case (one-shot per-user job, `start_new_session` re-parent, fixed env allowlist); restart/rebind tooling in the Runner (`drain-restart` shared start path `scripts/kaola-acp.py:666`, `rebind-host` `:3068`). **Narrowed gap (verified absence)**: no cross-platform service-supervision abstraction (health/backoff/reclaim policy unified across launchd/systemd/direct); `systemd-user` backend unverified on Linux in-repo. (v1's "no supervision abstraction" was too absolute — the Runner-level restart tooling exists.)

### L2 — ACP adapters
Existing: ten `platforms/*.yaml` capability manifests (models/tiers/effort/steer/`acp_mode_config_id`), ten `scripts/adapters/*.sh`, bridges (`kaola-zcode-acp.py`, `kaola-opencode-acp.py`, `kaola-dsh-acp.py`), shared holder advertising `holder_features`, vendored `claude-code-acp` with `DERIVATION.json`. Gap (verified by structure, not absolutes): capability data, adapter behavior, and bridges evolve on separate cadences with no single compatibility contract binding a manifest version to adapter/bridge versions.

### L3 — data contracts
Existing and **recognized**: three typed KPR schemas with allowlists (`scripts/kaola-record-contract.py:21-22` `kaola-heartbeat-prompt/2`, `kaola-delegator-heartbeat/1`, `kaola-dispatch-index/1`); KW's artifacts (`workflow-state.md`, mission ledger, `finalization-summary.md` headings, `chain-receipt.json` codeTreeHash, `.cache/final-validation.md`) under KW's JS. Verified absence: any shared contract registry or cross-implementation conformance suite between the two repos; the README drift is one symptom, not proof of necessity.

### L4 — module assembly
Existing: render pipeline with progressive-disclosure budgets (`templates/budgets.json`, generated-output-never-hand-edited), selective install (`install-local.sh --platform/--runtime|--skills-dir/--method/--no-orchestrator/--bin-links`), two-commit content/pin release model, install-time rendered-vs-installed verification (`scripts/render-skills.py:782-789`, `kaola-project-runner-install-verify/1`, Issue #107 diff). **Narrowed gap**: composition and verification are install-time; runtime selection exists only as narrow flags (`--launch-backend`), and post-install drift of installed copies has no ongoing monitor (the KW claim.js `4b02b82f→bf841bec` episode was found by ad-hoc measurement, not by a tool). (v1's "install-time only" and "undetected by any tool" are corrected to these precise statements.)

### Governance gap — Agent free file writing (owner-named; evidenced)
Typed single-writer records govern the three KPR schemas and KW's five artifacts; **outside those, cross-agent evidence is free prose files** — evidenced by this workspace's own record: CAD delivery-log authorization narration (#269), uncommitted 267/268 worktree residue (needed record commits), the `/tmp` exit-receipt reconstruction episode, CAD prose-only done-duty classes. Human prose and Git engineering evidence are legitimate and must remain; the verified absence is an ownership/query/integrity contract for the delivery-log/report class specifically — not a claim that "all files are ungoverned".

## 3. KPR+KW unified data mapping (corrected)

Recognized existing mechanisms: per-file `StateLock` (`kaola-dispatch.py:3556`) and atomic replace (`:1166-1171`, `os.replace`); dispatch↔task links (`link_dispatch_to_tasks` `:2127`, dispositions `:3676`); run↔issue↔ledger joins through KW finalize/sink (incl. `issue_numbers` set capture); resume/recovery receipts. Precise gaps: **cross-artifact** transaction/idempotency across heartbeat+index+delegator (three separate writes); a *uniform* identity scheme + general query spanning all artifact kinds (today each pair-link exists in its own format); general missing-record/duplicate-copy detection (existing detectors are artifact-specific: KW closure-audit, validate lane-integrity, state `unknown_paths`); cross-repo contract-version negotiation; installed-copy drift monitoring post-install. My earlier transient `state-missing` observation is recorded as **an unexplained transient** — the causal attribution to an atomic-replace window was a hypothesis, not established.

Storage options (fair, no preselection; **the owner's no-resident rule governs the KPR Host loop, not a prohibition on service architectures**):
1. **Files + unified access layer** — preserves Git evidence and single-writer rules; adds identity spine/queries/integrity; weakest cross-file transactions.
2. **Embedded DB** — real transactions/queries; new backup/secret/version story; must not bypass Git evidence (would need export discipline).
3. **Service/daemon storage** (Paseo/Temporal-style) — strongest consistency + remote access; cost is an operational service to run and secure — a **design cost/optional-need tradeoff**, not a prohibited option.

Contract inheritance (owner clarification): composable optional modules inherit one rule set rather than copying; requirements include dependency closure, contract versions, capability declarations, config composition, data ownership, and defined degradation when a module is absent; must prevent duplicated rules, dual writes, implicit permission inheritance; must **not erase per-module ownership or become an authorization-history store**. Pi's package split (contracts + conformance `pi-telemetry`, composition `chord`, durable `pi-durable`) is **one candidate pattern** — offered as a reference to study, not ranked "best" (no comparative verification was performed, and chord/durable internals are not yet source-inspected).

## 4. Fitting alternatives — fits vs reasons-against (fair)

| Candidate | Fits (verified) | Reasons-against / costs |
|---|---|---|
| Paseo | daemon control plane (`packages/server`: orchestration, WebSocket API, MCP); plugin system (`plugins/`, `plugin-examples/`); Apache-2.0 | adoption means running its daemon + adopting its session model; replaces rather than composes KPR's per-session ACP holders; plugin trust model differs from KPR permission boundaries — costs to weigh, **not disqualifications** |
| Pi | package-level contracts/conformance/composition/durable design pattern worth studying | TS ecosystem adoption cost; README-table claims need source-level verification before reuse; identity ("Py") unconfirmed |
| Cloudflare Workflows | durable execution, fibers | cloud/V8-isolate runtime; vendor-bound |
| Temporal | canonical durable workflow | server operational weight; workflow-as-code vs Git-evidence lifecycle tension |
| Restate | lighter durable runtime | runtime BSL; service to operate |
| T3 Code | agent control-plane UX | GUI surface, minimal data-contract reuse for KPR's headless layer |

## 5. Candidate directions for dot's analysis (options, not decisions)

- **O1 contract registry + generated validators/conformance** — would mechanically catch drift like README:88/104; cost: registry ownership and generator maintenance; the two repos' Python/JS split must both consume it. (v1 called this M1 "minimal viable" — demoted to option; #269's record explicitly needed **no new receipt artifact/framework**, and this research must not generalize that into a chosen framework.)
- **O2 identity spine over existing files** — uniform IDs + one access layer; no storage migration; misses cross-file transactions.
- **O3 module manifests** (capabilities, contract versions consumed, degradation-when-absent) — makes today's implicit optionality (e.g., Workflow "on if available") declared.
- **O4 typed receipt contract for the free-prose class** — generalizes the #269 lesson narrowly; must preserve human prose + Git engineering evidence and never become an authorization-history store.
- Sequencing, selection, or rejection of all four belongs to dot's analysis, then Fable review. No big-bang rewrite is proposed; any step must preserve KW's lifecycle ownership, KPR's single-writer rules, progressive disclosure, and the pin model.

## 6. Uncertainty register (outstanding)

- Pi `chord`/`pi-durable` internals: package presence verified, behavior/interfaces **not** source-inspected — next verification step if dot wants the pattern pursued.
- T3 Code / Temporal / Restate / ACP-upstream rows: official-link + search-verified only, no file-level license/layout check this pass.
- Owner-name resolutions unconfirmed by owner; "KWL" expansion unknown.
- The transient `state-missing` cause remains unexplained (hypothesis only).
- Maintenance snapshots are fetch-day reads (2026-10-07), not continuous monitoring.

---

## 7. Source-inspection appendix (v3, 2026-10-07 — read-only GitHub pages/raw/registry; no installs/clones)

**KPR locator self-verification** (bridge concern settled with evidence): `scripts/kaola-acp.py:666` is the docstring "The one presence decision for preflight and for the pre-spawn refusals ``start`` and ``drain-restart`` share"; `:3068` the `rebind-host` refusal receipt; `scripts/kaola-dispatch.py:666` is unrelated (`seat_projection` emit). The draft v2 locators were correct; quoted here so the match is self-evident.

**Pi** ([earendil-works/pi](https://github.com/earendil-works/pi); MIT; pushed 2026-10-06; 112,996 stars; branch `main`):
- `packages/chord` = `@earendil-works/chord`, "an application-composition runtime for systems assembled from plugins/extensions" (README). Actual `src/`: `api.ts, bundler.ts, index.ts, json.ts, node.ts, types.ts` + modules `context/ delta/ facets/ node/ services/`; `test/`, `PLANNING.md`. Interface-level reading still not done (files listed, contents unread) — remaining limit.
- `packages/durable` = `@earendil-works/pi-durable` — "A durable agent harness. Conversations, model turns, tool calls, and your own state are committed to storage **before anything is shown**"; **built on `@earendil-works/pi-ai` and `@earendil-works/chord`** (dependency direction verified). Exported surface (README): `Harness` (`open/root/resume/submit/configure/abort/reset/compact/fork/watch/viewState/taskGraph/usage/waitForTask/watchDoc`), `MemoryStorage`, `createRegistry`, `defineExtension/defineTool/defineDoc`, `wrapTool`, task kinds (`ToolTask/GenerationTask/CompactionTask`), **pluggable storage backends** (`openNodeSqliteStorage`, `openNodeJsonlStorage`, `openDurableObjectSqliteStorage`), and **conformance registrations** (`registerStorageConformance`, `registerEnvConformance`) — the contracts+conformance pattern is now verified in the package's own declared API, not just README prose. Marked experimental by its README.

**Paseo** ([getpaseo/paseo](https://github.com/getpaseo/paseo); Apache-2.0; 5,735 commits): `plugins/` actually contains per-agent `*-usage-source` plugins (claude/codex/copilot/cursor/grok/kimi/minimax/opencode-go/zai) plus `antigravity-provider` and `muse-provider` — real plugin kinds ("usage-source", "provider"), inferred from directory names; individual plugin extension-point code not opened (limit). Daemon = `packages/server` (orchestration, WebSocket API, MCP server) per package map.

**T3 Code** ([pingdotgg/t3code](https://github.com/pingdotgg/t3code); MIT; pnpm TS monorepo): top level `apps/ packages/ native/ infra/relay …`; supporting agents listed in README; provider/session/event source directories live under `apps/`/`packages/` and were **not** opened (limit; recorded rather than inferred).

**DSH upstream** (registry-checked): npm [`@deepseek-ai/dsh-acp`](https://www.npmjs.com/package/@deepseek-ai/dsh-acp) — description "Automation-only Agent Client Protocol server for driving DeepSeek Harness agents over JSON-RPC stdio"; repository **[github.com/deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)** (dir `packages/acp/acp`); latest `0.0.1-rc.1`, alpha `0.2.1-alpha.1` published 2026-10-03; license field **BSD-3-Clause at top level, most individual versions MIT** (mixed — recorded exactly). Matches KPR's in-repo facts (launcher-pinned harness, `agentInfo deepseek-harness-acp/0.0.1`).

**Distinct plugin/extension family — goose** ([block/goose](https://github.com/block/goose); Apache-2.0; Rust; 5,790 commits, 55k stars, active): extension via **MCP servers (70+ extensions) + 15+ model providers + ACP for subscription clients + custom distros** — a second, independent plugin-family pattern (protocol-standard extensions) distinct from Paseo's TS plugins and chord's in-process composition.

**Checked-at note**: all external facts above were read live on 2026-10-07 (GitHub pages / npm registry); no commit-SHA pinning was possible through the page fetches except where stated (Pi API gave branch/pushed-at; per-file SHAs not captured — limit). Ambiguous owner names remain candidate-only.

---

## 8. Worker-labor appendix (v4, 2026-10-07) — two independent deliveries, Host-accepted

Dispatch receipts: `opencode-KPR-i270-pi-interfaces` (holder `64b50e4b…`; stop receipt `stopped:true, exit 0, residual []`) and `devin-KPR-i270-kw-data-audit` (holder `b703c1af…`; same clean stop). Reports: `/tmp/kpr-i270-pi-interfaces-report.md` (4,711 B), `/tmp/kpr-i270-kw-audit-report.md` (3,862 B). The planning diagnosis for phase-1's zero dispatch is in issue comment 6030420812.

### 8.1 pi interfaces (opencode worker; source tree `eb326d2`)
chord exports `defineFacet/createFacetHost/createStaticFacetLoader/combineFacetLoaders/defineService/createRemoteServiceBinding/replicatedState`; facets register via `FacetEnvironment` (`use/observe/provide/provideMany/replicatedState/own/onActivate/onDeactivate`); `FacetHost.reload` swaps facets by id (runtime composition); `ReplicatedStateSource.attach()` = atomic snapshot + ordered frames; transports pluggable; strict JSON only. durable: `defineExtension` (named; reinstall replaces in place; conversations store extension *names* resolved against the current snapshot), `defineDoc<T>` (`kind/version/scope/history/fork/initial/migrate/checkpointWhen`), branded never-reused ids, `Storage` interface with Memory/SQLite/JSONL/DurableObject backends, atomic-commit invariant, and `registerStorageConformance/registerEnvConformance` with named case families. **Misfits that matter to KPR**: "One process owns a storage at a time; there is no cross-process locking" (in-process single-writer — does not transplant to KPR's multi-agent file world); no declarative manifest layer (contract versions/capabilities/degradation) for KPR's O3; experimental status. Net: O1/O4 pattern reference (typed versioned records + runner-independent conformance), not a dependency.

### 8.2 KW writer-path audit (devin worker; read-only, exact locators) — **corrects §3 of this document**
- **§3 claim "per-artifact single-writer" — INVERTED for KW**: `workflow-state.md` has writers across claim.js (`writeState` :907 callers :1292/:1734, `appendClosureBlock` :2628, archive stamps :2875/:4975/:6837) **and** sink-pr.js:526; `finalization-summary.md` has three script writers (:4404/:4427/:2894/sink-pr:539) **plus the run's Agent author**; `final-validation.md` is agent-recorded AND script-sanitized (:2908); the **mission ledger's primary writer is the Agent orchestrator itself** (claim.js:3547-3549), scripts only mkdir/move (:3551/:3084). KPR's typed schemas (heartbeat/delegator/index) retain their single-writer tool paths — the asymmetry is the finding.
- **"no cross-artifact transaction" — REFUTED**: the claim transaction writes exactly two artifacts (claim.js:1466 comment); finalize spans mirror-sync + archive move + ledger move + summary persist + commits; the sink pipeline mutates merge/archive/state-mirror/sink-receipt in one resumable transaction (SINK_STEPS `:1560`, idempotent step-skip `:2395`, abort hook `:1548`).
- **"single code-tree hash" — REFUTED**: `computeCodeTreeHash` (adaptive-schema.js:1124) is canonical for the finalize gate, but `computeLandableTreeDigest` (validation-runner.js:554, documented :1167-1172) is a second, deliberately different digest over the same band; recording the wrong one yields `final_validation_stale` — a concrete dual-implementation hazard **and** the likely mechanism behind this research session's own earlier `final_validation_stale` episode (record-tool hash vs gate hash).
- Verified as FIT: sink resumability/idempotency with named receipts (all locators above).

**Net effect on the research conclusion**: the unified-data problem is *sharper* than v2 stated — KW's own artifacts are multi-writer (including Agent-authored), with real multi-artifact transactions and a dual-digest hazard; KPR's three typed schemas are the strongest existing precedent for the contract/registry direction (O1). All corrections carry the worker's line locators; its full report is the original.
