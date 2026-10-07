# KPR minimal core + components — formal design draft v1 (2026-10-07)

Status: DRAFT for root personal review + owner-appointed Fable convergence (one bounded round, authorized). Not a final plan; no implementation/installation authorized by this document. Research corpus: docs/research/ @97551c75; Fable final + AB addendum @c61383b2; root corrections applied in place.

## 1. Current state → target

Today: ten generated platform worker Skills (transport-only), one generated orchestrator Skill (`kaola-project-runner`), one external Delegator Skill, render+install pipeline (`render-skills.py`, `install-local.sh`), per-session ACP holders + optional launchd broker, typed state tool (`kaola-dispatch.py state`), KW lifecycle scripts as a sibling repo. Monoliths: `kaola-dispatch.py` (208 functions) and `kaola-acp-holder.py` (50 functions) each span at least five distinct responsibilities.

Target: a **minimal core** + replaceable components. The core is a *library + contract set*, not a daemon shell and not a directory rename. Per owner: components are cut along ACTUAL source seams (measured below), not a predecided count; no per-function microservices; dependencies are explicit contracts; subtraction (remove/replace/retire/uninstall) is a first-class operation; KPR+KW remain optional modules sharing runtime norms without forcing synchronized consumer upgrades or a central credential store.

## 2. Core (irreducible, per measured source)

What must stay together because everything else depends on it and splitting it adds contracts without removing coupling:

- **Identity model**: platform/session/holder_instance_id/native-id/repo canonicalization (`canonical`, `normalize_id`, `worker_event_id`, `holder_of`, `assignment_identity`), plus the record-dir layout and schema names (`kaola-heartbeat-prompt/2`, `kaola-delegator-heartbeat/1`, `kaola-dispatch-index/1`). ~Small; zero I/O deps.
- **Process facts**: pid/liveness/spawn-time/argv anchor/process-tree groups (`process_alive`, `libproc_ps`, `process_table`, `child_groups`, `spawn_time_matches`, `holder_argv_anchor`, `holder_identity` in kaola-acp.py). Depends only on identity model. This is the proven single-writer+identity substrate (#273 fix rides it).
- **Atomic state access**: `read_state_file`/`atomic_write`/`StateLock` + `kaola-record-contract.py` allowlists. Depends on identity only.
- **Contract registry (thin)**: schema names + key allowlists + version numbers consumed by both KPR and KW (closes the Python/JS dual-implementation divergence; generated validators, conformance suites optional per module).

## 3. Components (cut along measured seams)

Each row: current source (function clusters with line anchors), target owner, why not core, inputs/outputs, typed errors, version, data owner, dependencies, independent tests, install/load optionality, replace/uninstall, cross-component evidence. **Owners** = component module in the same repo initially (not separate services).

| # | Component | Current source (measured) | Why not core | Key interfaces / typed errors | Deps |
|---|---|---|---|---|---|
| C1 | Session/process lifecycle | kaola-acp-holder.py: parse_dispatcher/parse_heartbeat_host/read_heartbeat_file/start_epoch/live_spawn_entries/worker_tree_groups/dispatched_worker_groups/scrub/run_probe; kaola-acp.py start/stop/status/drain-restart/rebind-host | holder orchestration policy, not identity facts | receipts (`schema_version 3`, `stopped/exit/residual_pids`), `holder-lost`, `holder-not-ready` | core identity+process facts |
| C2 | ACP transport adapters | platforms/*.yaml, scripts/adapters/*.sh, kaola-zcode-acp.py / -opencode- / -dsh-, vendor claude-code-acp | per-platform variance; catalogs are data not logic | manifest fields, `acp_mode_config_id`, per-platform quirks docs | core identity |
| C3 | Events | kaola-acp-holder.py worker_event_id/attention_fingerprint; kaola-acp.py observe/capture/follow; events.jsonl rotations | consumers differ (Host UI vs state) | bounded capture receipts, `truncated` fields, cursor discipline | C1 |
| C4 | Current-state access | kaola-dispatch.py state CRUD (init/update/retire/view/check/migrate; 47-fn cluster incl. task/hold/alert/decision records) | record kinds evolve; core keeps only atomic access | StateRefusal codes (`conflict`, `retire-unmet`, `schema-unsupported`...), rev numbers | core atomic access |
| C5 | Dispatch/admission facts | kaola-dispatch.py execute/collect/project/delegator_seats (27-fn cluster; dispatch_links, seat_projection) | admission policy is Agent judgment over tool facts; the tool only records facts | plan schema, index schema, dispositions, `requirement-unmet`, `resource-conflict`, `shared-occupied` | C4, C3, core |
| C6 | Bounded maintenance/recovery | recovery-input/checkpoint; kaola-compact-recovery.py; kaola-project-compact-notice.py; sideagent binding+recipe | optional (absent → inputs simply queue) | recovery_input seq, checkpoint batches, `signal-unverified` | C4, C3 |
| C7 | Generation/install/versioning | render-skills.py, install-local.sh, budgets.json, accepted-revision pin, install-verify | pure build-time; absent at runtime | render receipts, budget check, pin gate, `kaola-project-runner-install-verify/1` | none (consumes core schemas) |
| C8 | KW engineering bridge | Kaola-Workflow repo (READ-ONLY design partner): claim/finalize/sink, chain receipts | separate ownership & artifact model already | workflow-state.md, ledger, `chain-receipt.json` codeTreeHash | C4 contract registry |

**Not components**: Agent judgment (planning/selection/acceptance) stays in Agents by definition; #267 escalation stays per-task inside C4/C5 facts.

## 4. Mermaid dependency DAG

```mermaid
graph TD
  CORE[Core: identity + process facts + atomic state + contract registry]
  C1[C1 lifecycle holders] --> CORE
  C2[C2 ACP adapters] --> CORE
  C3[C3 events] --> C1
  C4[C4 state records] --> CORE
  C5[C5 dispatch/admission] --> C4
  C5 --> C3
  C6[C6 maintenance/recovery] --> C4
  C6 --> C3
  C7[C7 generate/install/version] --> CORE
  KW[C8 KW bridge] --> C4
  AGT[Agent judgment] -.facts only.-> C5
  AGT -.state.-> C4
```

No cycles; the core is the only shared substrate; C2 and C7 depend on nothing but the core (independently skippable at runtime/install time).

## 5. Optional install / runtime loading / subtraction

- Install-time optionality already exists per component flags (`--no-orchestrator`, `--platform`, link|copy). Formalize: each component declares `requires`/`provides` in its manifest (same grammar as plan `requires` — capability ids, not scopes).
- Runtime loading: C6 is the pilot (absent → recovery inputs queue; present → node batches). Same pattern for C8 (Workflow on if available). No new loader machinery — the existing capability advertisement (`holder_features`) is the runtime probe.
- **Subtraction**: every component defines (a) uninstall = remove generated payload + its config namespace; (b) retire = stop loading, keep data namespace readable via core contract registry; (c) replace = same provides-contract, swapped implementation, cross-component tests must pass unchanged; (d) data ownership stays with the consuming project (`.kaola/`), never moved into a component. Deleting a module must NOT force synchronized consumer edits: consumers depend on contracts (schemas + typed errors), and contract versions are additive-with-refuse (unknown version → refuse with named id, current behavior) — the proven #268/#273 refusal style.

## 6. Failure, fencing, upgrade semantics (design, all UNTESTED until staged)

- Single-writer per artifact stays (StateLock/atomic write). Cross-store fencing: any future shared store (B-line option) requires an explicit **handoff token** (lease with epoch) — **un-handed-off fallback dual-write is forbidden** (root constraint).
- Startup contention: last-writer detection by holder_instance_id epoch (already the exact-stop guard substrate); a newer holder supersedes, older refuses.
- Crash recovery: C1 holder exit does not lose C4 state (files+locks); C6 re-binds queued inputs; no auto-restart (Host-on-demand boundary unchanged).
- Version compat: contract registry versions; reader-older → typed refuse (never silent). Cross-version data migration staged per component with reader-before-writer rollout (Fable C6 fact: current validator already refuses unknown keys → fail-closed).
- idle-exit is a *candidate* policy for optional components only; it must not weaken the resident-service goal (owner A/B decision) nor the per-user/per-machine lightweight core direction (B0).

## 7. Cross-component test evidence (what proves a cut)

Each component ships its own suite plus one integration contract test per edge in the DAG (C1→CORE identity, C5→C4 dispositions, C6→C4 recovery seq...). A module suite passing alone never replaces cross-module migration/retirement proof (root constraint). Pilot candidates from current reality: #274 package-closure test (C7 proving C6's helper closure), #273 real-entry suites (CORE process facts through C1 CLI and C5 consumer).

## 8. Open decisions for root/Fable convergence

1. Core library language/packaging: single python package consumed by generated skills (recommend) vs multi-language contract generation.
2. C4/C5 boundary: whether seat_projection belongs in C5 facts or core (recommend C5; core stays free of grant semantics).
3. C8 contract-registry co-ownership with KW maintainers.
4. Whether C7 gains a `--component` install grammar now or after the pilot.
5. Staging order (see migration.md) and the B0 resident-core pilot scope (lifecycle+events first, per Fable AB).
