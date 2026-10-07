# ADRs — KPR minimal core + components (2026-10-07 draft)

Format: Context / Decision / Consequences. Each ADR cites its evidence locator. Status: PROPOSED — root + Fable convergence pending; none is decided.

## ADR-1: The resident core is the accepted target; staging starts as a shared library
Context: owner ACCEPTED the B direction — per-user/per-machine lightweight RESIDENT core, lifecycle+events first (B0). The A/B split forbids letting the minimal-patch line constrain B; it does NOT forbid the resident form.
Decision: the core's runtime form is the resident core (B0). Staging begins by extracting the core as a shared library so the component cut is provable and the resident pilot hosts real code, not a rewrite. The library is the resident core's implementation, not an alternative to it; "no daemon" is NOT the B default at any stage.
Consequences: library-first is a build order, not a direction change; P5 measures the resident pilot against the nine axes as planned evidence, not as permission to re-decide the direction. Evidence: kaola-acp.py:1680-1693/1537-1546 (identity), :1166/:3556 (atomic+lock).

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

## ADR-5: No un-handed-off fallback dual-write; fencing needs a real lease
Context: root constraint on B fencing; #273 shows identity checks are time-bounded snapshots. ACCURACY: `holder_instance_id` is a unique identity, not an ordered epoch — today's exact-stop guard compares identity equality, not seniority.
Decision: any dual-write path (store migration, core fallback) requires an explicit handoff token: a monotonic lease epoch with acquisition, renewal, expiry and contention arbitration specified in P1 and drilled in P5; without a valid lease the older writer keeps single ownership and the newer refuses with a typed `lease-held` error.
Consequences: brief unavailability instead of split-brain; the lease design itself is unimplemented until P1; handoff drills mandatory before any shared store. Evidence: root A/B decision; StateLock single-writer; kaola-acp.py holder guard (identity equality).

## ADR-6: Recipes bind to stable pinned sources only
Context: AI event 105633 — the consumer sideagent recipe's `runner`/`state_tool` named the MUTABLE DEV checkout; a dev render changed the adjacent main-skill-build the skew baseline read, so the consumer's build-skew check refused a legal release (expected 4868c8b6 vs installed 0eeb0db6; installs and the accepted checkout were verified untouched). Not a capacity-incident artifact.
Decision: recipe sources must name installed Skill roots or verified accepted checkouts (guidance shipped in sideagent-node.md @93662173); bind-time source verification that refuses mutable-dev sources is a P3 candidate with a negative fixture, not implemented.
Consequences: dev checkouts never become implicit consumer dependencies. Evidence: AI event 105633 (recipe readback + main-skill-build expected/installed deltas); stable accepted checkout kaola-project-runner-accepted @3de9f61 (installed build 0eeb0db6, verified).

## ADR-7: KW is an optional module sharing runtime norms, never merged repos
Context: KPR+KW unified data management goal; distinct ownership must survive.
Decision: C8 bridge consumes the core contract registry; KW keeps its lifecycle scripts and artifact ownership; shared schemas get generated validators on both sides (closes the dual-implementation divergence).
Consequences: either side can ship alone; contracts change additively per ADR-3. Evidence: KW README drift; final-validation dual-digest hazard (research §3).
