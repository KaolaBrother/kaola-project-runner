# ADRs — KPR minimal core + components (2026-10-07 draft)

Format: Context / Decision / Consequences. Each ADR cites its evidence locator. Status: PROPOSED — root + Fable convergence pending; none is decided.

## ADR-1: The core is a library + contract registry, not a daemon
Context: Fable AB recommends B0 per-user/per-machine resident core (lifecycle+events first); root approved B direction but also demands subtraction-first and forbids preselecting daemon/DB (A/B decision).
Decision: core = identity model + process facts + atomic state access + thin contract registry, as a library consumed in-process by components. A resident core becomes a B-line *pilot* (B0) only if staged evidence shows cross-process coordination needs it; files+locks remain the A-line substrate.
Consequences: no new process to operate today; B0 remains possible without re-cuts (the library is what a resident core would host). Evidence: kaola-acp.py:1680-1693/1537-1546 (identity), :1166/:3556 (atomic+lock).

## ADR-2: Components are cut along measured function-family seams
Context: owner requires actual-source cuts, no predecided count, no microservices.
Decision: the eight components (C1–C8) follow the measured clusters (design.md §3 line anchors); future re-cuts allowed with the same evidence rule.
Consequences: initial cut is coarse; refinement is subtraction of responsibility, not a breaking event. Evidence: dispatch.py 208-fn / holder.py 50-fn inventories in design.md.

## ADR-3: Unknown contract versions refuse, never degrade silently
Context: #268 selection continuity + validator allowlists already refuse unknown keys (fail-closed, Fable C6); README drift showed silent divergence cost.
Decision: contract registry versions are additive; an older reader meeting a newer artifact refuses with the named id+version (current behavior formalized). Degrade lists are per-contract and explicit.
Consequences: reader-before-writer rollout discipline for any breaking change; no silent forward-compat. Evidence: record-contract allowlists; KW README:88/104 drift.

## ADR-4: Subtraction is a designed operation with data ownership fixed
Context: owner: deleting a module must not force synchronized consumer edits; data belongs to the consuming project.
Decision: uninstall/retire/replace defined per component (design.md §5); data namespaces stay in `.kaola/` under core contract registry; consumers depend on contracts only.
Consequences: a replaced component must pass the SAME cross-edge contract tests; retirement keeps data readable read-only. Evidence: #274 (package closure as a subtraction-class bug), AGENTS #255 continuous-improvement duty.

## ADR-5: No un-handed-off fallback dual-write
Context: root constraint on B fencing; #273 shows identity checks are time-bounded snapshots.
Decision: any dual-write path (store migration, core fallback) requires an explicit handoff token (lease+epoch); without it the older writer keeps single ownership and the newer refuses.
Consequences: brief unavailability instead of split-brain; handoff drills mandatory in staging. Evidence: root A/B decision; StateLock single-writer.

## ADR-6: Recipes bind to stable pinned sources only
Context: AI event-105633 — a consumer recipe pointed at a mutable dev checkout; dev render drifted its expected build and the skew check refused a legal release.
Decision: sideagent recipe `runner`/`state_tool` must name installed Skill roots or verified accepted checkouts (guidance shipped in sideagent-node.md @93662173); binding-author tooling should verify the source build at bind time (candidate, not implemented).
Consequences: dev checkouts never become implicit consumer dependencies. Evidence: /tmp/vrpai-kpr-cap-incident-evidence.json family; kaola-project-runner-accepted @3de9f61.

## ADR-7: KW is an optional module sharing runtime norms, never merged repos
Context: KPR+KW unified data management goal; distinct ownership must survive.
Decision: C8 bridge consumes the core contract registry; KW keeps its lifecycle scripts and artifact ownership; shared schemas get generated validators on both sides (closes the dual-implementation divergence).
Consequences: either side can ship alone; contracts change additively per ADR-3. Evidence: KW README drift; final-validation dual-digest hazard (research §3).
