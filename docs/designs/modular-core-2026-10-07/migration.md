# Migration phases — KPR minimal core + components (2026-10-07 draft)

Status: PROPOSED staging; each phase gates on its own acceptance evidence + root review. Research/B-design completion does NOT close any migration item. No early install of dirty trees or daemons.

## Phase map (issues → components → acceptance)

| Phase | Scope | Issues | Component | Acceptance (concrete) | Rollback |
|---|---|---|---|---|---|
| P0 | SHIPPED TO MAIN — but pushed main is NOT a release or an install: #273/#274 remain OPEN and consumers have NOT installed the fixes (next release/pin cycle carries them; Seats implications at that boundary). #271 six-step acceptance + #272 loop execution evidence delivered (ff1caef6/cbe1f2ae). | #273 #274 (shipped-to-main); #271 #272 (evidence delivered) | C7/C5/C6 edges | 5cef759a/93662173/9498af34/e7aea057/cbe1f2ae (later corrections: 7cb361d3 partial ruling, aa1c1444 cursor correction) | git revert per commit; no data migration |
| P1 | Extract core library (identity+process+atomic state+contract registry) as an internal package; components import it | (new, to file) | CORE | 208-fn/50-fn inventories split without behavior change: full inventory green at same HEAD; import graph test (no component reaches around core) | revert import indirection; single-file restore |
| P2 | C7 gains component manifests (`provides`/`requires` grammar = capability ids) + `--component` install selection | (new) | C7 | render --check verifies manifests; install-verify receipt per selected set; subtraction dry-run (uninstall a component's payload, suites for remaining set green) | re-render full set; no consumer data touched |
| P3 | C6 maintenance optionality pilot (recovery inputs queue without node; recipe bind-time source verification per ADR-6) | #271-adjacent | C6 | recovery-input queued≠lost with node absent; bind-time verification refuses mutable-dev source (negative fixture); deployment-isolation regression | restore binding; inputs replay |
| P4 | C4/C5 record-contract registry shared with KW (generated validators both sides) | coordination with KW maintainers | C8/CORE | dual-implementation divergence closed: same schema fixture validated identically by python+js generated validators; conformance suite runs in both repos | per-repo revert; additive versions only |
| P5 | B0 resident-core pilot (per-user/per-machine, lifecycle+events). Direction ACCEPTED — no re-confirmation. Technical gates (not owner choices): P1 green, lease design drilled, event-cursor semantics designed. KW coordination (P4) does NOT block a lifecycle/events pilot — it is parallel, not a prerequisite. Engineering recommendations (NOT owner questions per root): Mac supervision = existing launchd mechanisms, Linux = systemd equivalents; B0 pilot keeps C2 adapters per-session. Only a change that genuinely alters the operational/deployment COMMITMENT goes to the Owner — the previously catalogued eight choices are NOT revived as gates. | #270 B-line | CORE+C1+C3 | nine-axis measurement on the running pilot; fencing/handoff drills; idle-exit candidate only | stop pilot core; holders continue independently per §6a (never killed); no dual-write per ADR-5 |

## Order rationale and dependencies
P1 unblocks everything (contracts live in core). P2/P3 are independent after P1. P4 (KW shared validators) is EXTERNAL coordination and runs in parallel — it does not gate the P5 lifecycle/events pilot, because the pilot's core surface (identity/process/state/events) does not depend on KW artifact schemas. Staged implementation is not early installation: nothing here installs a daemon or upgrades consumers before its phase evidence.

## Technical gates vs owner value choices (explicit)
- Technical gates (Host/engineering decide, evidence-bound): component cut completeness (inventory UNASSIGNED=0), import-graph test, manifest grammar, bind-time verification fixture, lease design + drills, event cursor semantics, reader-fallback set.
- Owner value choices (user decides, with options/costs): only genuine operational/deployment commitment changes; the previously catalogued eight choices are NOT revived as gates. Supervision (launchd/systemd) and adapter placement are ENGINEERING recommendations per the root ruling. D4 schema fields remain behind the replay-test gate as a technical decision with owner visibility.

## What is explicitly NOT migration
- A-line fixes (#269 consumer-owned cleanup; #271/#272/#273/#274 follow-ups) proceed independently.
- Consumer recipe repair (AI event-105633 class) is the original bridge's work, not a KPR migration step; KPR ships only the guidance + (P3) bind-time verification.
