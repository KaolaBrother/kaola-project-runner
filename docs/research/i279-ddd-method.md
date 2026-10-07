# DDD (Triple-D) method for issue #279 — agent context units

Read-only independent research. `[SRC]` = primary-source conclusion (verbatim quotes in
`/tmp/kpr-279-source-register.md`). `[DERIV]` = our derivation. `[ASSUMPTION]` = consumer source
**not read**. No implementation, no consumer writes. KPR evidence: commit `889f12bb`,
`docs/designs/modular-core-2026-10-07/design.md`; corpus `docs/research/…2026-10-07.md`.

## 1. Strategic DDD (source conclusions)

**Subdomains: core / supporting / generic.** Microsoft's official guide `[SRC]`: "Core subdomains
provide a competitive advantage… Supporting subdomains keep the business operational but don't
differentiate it… Generic subdomains represent problems that the industry already solved." Evans
(via martinfowler.com/bliki/BoundedContext.html) `[SRC]`: "total unification of the domain model
for a large system will not be feasible or cost-effective."

**Bounded context.** `[SRC]` "Bounded Context is a central pattern in Domain-Driven Design. It is
the focus of DDD's strategic design section which is all about dealing with large models and
teams." It is set by *language and model-representation* changes, not file layout.

**Ubiquitous language.** `[SRC]` "the practice of building up a common, rigorous language between
developers and users… software doesn't cope well with ambiguity." MS `[SRC]`: "Each bounded
context can have its own ubiquitous language, which means that the same word (like *account*) has
different meanings in different contexts."

**Context mapping.** Brandolini (InfoQ) `[SRC]`: a context map is "a working tool that allows us
to map a fuzzy situation, so a somewhat fuzzy look is necessary" — not precise UML. Relationship
types `[SRC]`: Customer-Supplier; Open Host Service + Published Language; Anti-Corruption Layer;
Separate Ways. DDD's split `[SRC]`: "In strategic DDD, you define the large-scale system
structure… Tactical DDD provides design patterns."

## 2. Tactical patterns — and how they differ from strategic

Tactical patterns model **inside one bounded context**; they do not decide boundaries (that is
strategic: a language change). Tactical cohesion must not become a boundary merely because classes
cluster.

- **Aggregate + invariants.** `[SRC]` "An aggregate will have one of its component objects be the
  aggregate root. Any references from outside the aggregate should only go to the aggregate
  root… Transactions should not cross aggregate boundaries." Vernon IDDD ch10 rule `[SRC]`:
  "Model True Invariants in Consistency Boundaries."
- **Entity.** `[SRC]` "distinct identity that runs through time and different representations."
- **Value object.** `[SRC]` "matter only as the combination of their attributes"; "value objects
  should be immutable."
- **Repository.** `[SRC]` "mediates between the domain and data mapping layers, acting like an
  in-memory domain object collection."
- **Domain service.** `[SRC]` "A standalone operation within the context of your domain" (IDDD
  ch7 "Services") — not an application service.
- **Domain events.** `[SRC]` "capture things that can trigger a change to the state of the
  application"; "source data… is immutable." Optional and architecture-heavy — not a mandate for
  event sourcing/CQRS.

Difference to hold: strategic = cross-context decomposition, language, mapping, team topology;
tactical = within-context mechanics (aggregate = consistency boundary ≠ context).

## 3. Architecture — isolation, contracts, ACL

- **Monolith vs microservices.** `[SRC]` "don't even consider microservices unless you have a
  system that's too complex to manage as a monolith"; "you shouldn't start a new project with
  microservices." AWS `[SRC]`: "Deciding between microservices or monoliths should be made on a
  case-by-case basis."
- **Process isolation ≠ domain boundary.** `[SRC]` "services map to runtime processes, but that is
  only a first approximation." A separate process/lib is an engineering convenience; a context is
  a language/model boundary. The two often correlate, but are not the same.- **Data ownership per context.** `[SRC]` microservices "prefer letting each service manage its
  own database"; transaction boundary = aggregate boundary, so cross-context coordination becomes
  eventual/compensating, not a shared transaction.
- **Contracts, schema, versioning.** `[SRC]` "we build services that share contracts, not types";
  Tolerant Reader: "be conservative in what you do, be liberal in what you accept from others";
  consumer-driven contracts make consumer expectations executable.
- **Anti-corruption layer.** `[SRC]` "Isolate the different subsystems by placing an
  anti-corruption layer between them. This layer translates communication between the two
  systems." Use when semantics differ; keep business rules out of the translator.
- **Modular-monolith engineering case.** Spring Modulith `[SRC]`: a module has a *provided
  interface*, *internal implementation*, and *required interface*, verified structurally. (Kieran
  Scott / "modulithics" was unreachable; not used.)

## 4. Mapping KPR + KW + consumers `[DERIV]`

Components are **not** bounded contexts (design.md §3: cuts follow measured function seams). By
**language/model**, KPR has three runtime contexts:

| Context | Strategic type | Modules (design §3) | Ubiquitous-language candidates |
|---|---|---|---|
| **KPR session-runtime** | core (differentiator: reliable ACP session lifecycle) | CORE identity/process, C1 lifecycle, C2 adapters, C3 events | holder, holder_instance_id, session, native-id, receipt, exit/residual_pids, event cursor |
| **KPR orchestration-state** | supporting | C4 state, C5 dispatch, C6 recovery | task, hold, alert, decision, dispatch, StateRefusal, revision, lease/handoff, `signal-unverified` |
| **KPR build/install** | generic (industry-solved tooling) | C7 render/install | manifest, `provides`/`requires`, budget, pin, install-verify |

**KW = a separate bounded context** (design §3 row C8: "separate ownership & artifact model
already"). Evidence of a genuinely different model `[SRC: in-repo research §3]`: KW artifacts are
multi-writer with resumable step-receipt workflows and a dual code-tree digest, unlike KPR's
single-writer `.kaola/` state. **Relationship** = Customer-Supplier / Published Language with an
**ACL at C8** for the dual-digest skew (design §5, ADR-7: "one contract with two named views").
KW source was not re-opened; claims come from our in-repo design/research records.

**VRPAI / CAD = external contexts, source NOT read** — every statement below is `[ASSUMPTION]`:
`[ASSUMPTION]` they are production apps with their own task/authorization language; `[ASSUMPTION]`
KPR consumes them across a consumer-bridge contract (Open Host Service / Published Language), so
their model is upstream and must be translated at an ACL, never imported into
orchestration-state. Treat all of it as a hypothesis to verify from their bridge evidence.

## 5. Deliverable: Agent WORK-UNIT CONTEXT PACK

One independent work unit = one aggregate-like change inside one context.

1. **Domain vocabulary** — the exact terms (this context's ubiquitous language) + dictionary/allowlist pointer; no re-coined synonyms.
2. **Inputs / outputs** — typed artifacts read and produced (schema + version).
3. **Invariants** — the few rules that must hold across the unit (uniqueness, single-writer, monotonicity, authority); they define the consistency boundary.
4. **Dependency contracts** — allowed consumers/providers, pinned contract versions, typed errors.
5. **Acceptance criteria** — observable outcomes, including refusal paths.
6. **Allowed-change surface** — files/APIs the unit may touch; anything else refuses.

Testing split: **independent development tests** (unit + invariant) and **integration/consumer
contract tests** (over the real seam; consumer-driven assertions). Boundary evolution: **split**
when one term gains two meanings or two change-rates; **merge** when changes always co-occur
("if you find yourself repeatedly changing two services together, that's a sign that they should
be merged" `[SRC]`); **delete/retire** = uninstall + read-only export, with data owner = consuming
project.

### Filled KPR example — C4-state work unit "retire a record"

- Vocabulary: task/hold/alert/decision, `retire`, StateRefusal, revision.
- In/out: current-state JSON (C4-owned version) → updated current-only state.
- Invariants: single writer under `StateLock` atomic replace; `retire-unmet` refusal when links unmet; monotonic `rev`; **no tombstone/history of handled rows** (owner rule, AGENTS.md).
- Dependency contracts: CORE atomic access; C5 dispatch links; typed refusals named by id+version.
- Acceptance: happy path + refusal path + reopen-safety; reader-older → typed refuse.
- Allowed surface + evolution: C4 state functions and schema only (no C5 writes); a second meaning of "hold" → candidate split; retire = keep-data read-only export (design §5).

### Counter-example (pattern does NOT apply)

`[ASSUMPTION]` A one-line consumer (VRPAI/CAD) config/document fix — e.g. adjusting a cadence
value or doc string: small surface, single-agent edit, no invariant worth isolating, no new
vocabulary. A context pack adds ceremony, not safety; a direct reviewed edit with a focused check
is correct. The method must **not** auto-apply at any scale.

## 6. Adoption, non-promises, costs, open questions

**Incremental path** `[DERIV]`: (1) run the pack once on an existing KPR unit (C4) as a prose
sidecar, no code change; (2) add machine checks only where they already exist (render `--check`;
existing contract suites); (3) split/merge only on observed language/change-rate evidence;
(4) define the retire/export path before any cut.

**Validation checks**: unit tests for the stated invariants; one cross-edge contract test per
dependency; a refusal-path test; a boundary test that a foreign-context write is refused.
**Explicit non-promises** `[DERIV]`: this does **not** eliminate agent context limits; does **not**
auto-fit any scale; is **not** a mandate for event sourcing, CQRS, microservices, or
one-process-per-context; does not make contexts permanent.

**Cost / counter-example**: packs cost writing and maintenance and can drift from code; premature
contexts fragment a small codebase (Microservice Premium `[SRC]`); ACLs add latency and another
component to run `[SRC]`. Use only where an invariant or semantic gap justifies the cost.

**Bounded open questions**: (Q1) is KW truly *one* context or several (unread at source this
round)? (Q2) do VRPAI/CAD bridges expose a Published Language or an ad-hoc field set?
`[ASSUMPTION]` only. (Q3) do C4/C5 share one language (one context) or two? They share one state
store though design §3 lists them separately — resolve from source. (Q4) can the pack be validated
without a new gate (reuse the #268/#273 refuse style)?

_Research only. No root/Fable review claim; not a reopening of the B design._

---

## 7. Component-contract sketch for the optional DDD strategy component (Host, per user positioning)

This frames DDD as an installable/uninstallable strategy component in the converged core design — an optional extension, never a B0/migration precondition.

- **Responsibilities**: domain-modeling input to boundary decisions (vocabulary/invariant/change-rate evidence, never auto-partitioning); work-unit context-pack generation from existing records; mapping suggestions (marked ASSUMPTION where source unread); boundary-evolution recommendations with evidence. **Non-responsibilities**: no final value/architecture/acceptance judgment (Host/owner), no project management totality claim, no machine domain split.
- **Data ownership**: reads existing project records + design docs (read-only); owns ONLY its generated packs/mappings in the consuming project's `.kaola/` namespace (C4-style single-writer), never a second authority store; no authorization content enters its outputs.
- **Version compatibility**: contract-version field on packs; unknown-version → typed refuse (ADR-3 style); optional-field tolerance stated per-pack.
- **Failure degradation / uninstall**: absent → work proceeds exactly as today (no pack is a gate); retire → read-only export of packs; replacement is any equivalent pack producer behind the same pack schema.
- **Applicability criteria (when to install)**: multiple bounded languages or change-rates observed; invariant/consistency boundaries worth isolating; cross-context collaboration costing rework. **Simplified path**: single-context small projects use a one-paragraph vocabulary + invariants + allowed-change note (the pack minus ceremony) — the counter-example rule governs.
- **Validation design**: pack-vs-code drift check reusing existing suites (no new gate); one cross-edge contract test per dependency named in a pack; refusal-path test; boundary-evolution decisions cite observed evidence. Reuse #268/#273 refuse style (Q4 resolution proposal).

These are the component's own contract rows; adoption itself remains the owner's decision.
