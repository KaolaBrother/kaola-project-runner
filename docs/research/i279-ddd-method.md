# DDD (Triple-D) method for issue #279 — agent context units

Read-only independent research. `[SRC]` = primary-source conclusion (verbatim quotes in
[i279-ddd-source-register.md](i279-ddd-source-register.md)). `[DERIV]` = our derivation. `[ASSUMPTION]` = consumer source
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
  a language/model boundary. The two often correlate, but are not the same.
- **Data ownership per context.** `[SRC]` microservices "prefer letting each service manage its
  own database" describes a microservice deployment preference, not a universal DDD requirement.
  A modular monolith may share physical storage while preserving logical ownership. Transaction
  scope, synchronous collaboration, eventual consistency and compensation are explicit design
  choices constrained by real invariants, not deductions from a context label.
- **Contracts, schema, versioning.** `[SRC]` "we build services that share contracts, not types";
  Tolerant Reader: "be conservative in what you do, be liberal in what you accept from others"
  (tolerance is per schema; permission- and write-bearing fields are never tolerated when unknown —
  [i279-ddd-contract-tests.md](i279-ddd-contract-tests.md));
  consumer-driven contracts make consumer expectations executable.
- **Anti-corruption layer.** `[SRC]` "Isolate the different subsystems by placing an
  anti-corruption layer between them. This layer translates communication between the two
  systems." Use when semantics differ; keep business rules out of the translator.
- **Modular-monolith engineering case.** Spring Modulith `[SRC]`: a module has a *provided
  interface*, *internal implementation*, and *required interface*, verified structurally. (Kieran
  Scott / "modulithics" was unreachable; not used.)

## 4. Mapping KPR + KW + consumers `[DERIV]`

Components are **not** bounded contexts (design.md §3: cuts follow measured function seams). By
**language/model**, the following are THREE CANDIDATE context groupings, not established boundaries.
Their core/supporting/generic labels are hypotheses about product value, not classifications
based on technical layers. Validate each against domain-expert language, invariant/consistency
evidence and observed change coupling; orchestration may be a differentiator rather than supporting:

| Candidate context | Candidate strategic type (hypothesis) | Modules (design §3) | Ubiquitous-language candidates |
|---|---|---|---|
| **KPR session-runtime** | core (differentiator: reliable ACP session lifecycle) | CORE identity/process, C1 lifecycle, C2 adapters, C3 events | holder, holder_instance_id, session, native-id, receipt, exit/residual_pids, event cursor |
| **KPR orchestration-state** | supporting | C4 state, C5 dispatch, C6 recovery | task, hold, alert, decision, dispatch, StateRefusal, revision, lease/handoff, `signal-unverified` |
| **KPR build/install** | generic (industry-solved tooling) | C7 render/install | manifest, `provides`/`requires`, budget, pin, install-verify |

**KW = a candidate separate domain model, whose internal context count is UNVERIFIED**. Design §3
row C8 records separate ownership/artifacts, which alone does not prove a single bounded context.
Evidence suggesting a different model `[SRC: in-repo research §3]`: KW artifacts are
multi-writer with resumable step-receipt workflows and a dual code-tree digest, unlike KPR's
single-writer `.kaola/` state. **Candidate relationship** = Customer-Supplier / Published Language, with a possible
**in-process translation at C8** for differing digest semantics (design §5, ADR-7: "one contract with two named views").
KW source was not re-opened; claims come from our in-repo design/research records.

**VRPAI / CAD = external contexts, source NOT read** — every statement below is `[ASSUMPTION]`:
`[ASSUMPTION]` they are production apps with their own task/authorization language; `[ASSUMPTION]`
KPR consumes them across a consumer-bridge contract (Open Host Service / Published Language), so
their model is upstream and is translated at that boundary rather than imported into
orchestration-state; an in-process translator may suffice, and a separate process is a deployment
choice. Treat all of it as a hypothesis to verify from their bridge evidence.

## 5. Deliverable: Agent WORK-UNIT CONTEXT PACK

An aggregate is a consistency boundary; an Agent work unit is a bounded, verifiable change.
They do NOT map one-to-one. Decompose tasks by change coupling and acceptance surfaces. A task
may touch several aggregates or contexts; name the collaboration contracts, data writers,
invariants and integration evidence for those boundaries rather than prohibit the task.

1. **Domain vocabulary** — the exact terms of the context(s) the unit touches (their ubiquitous language) + dictionary/allowlist pointer; no re-coined synonyms.
2. **Inputs / outputs** — typed artifacts read and produced (schema + version).
3. **Invariants** — the few rules that must hold across the unit (uniqueness, single-writer, monotonicity, authority); they name the consistency boundaries the unit must respect (one or several).
4. **Dependency contracts** — allowed consumers/providers, pinned contract versions, typed errors.
5. **Acceptance criteria** — observable outcomes, including refusal paths.
6. **Expected-change surface** — files/APIs and interfaces anticipated for the unit. This is
   planning information, not a new global refusal gate. If a legitimate dependency-contract
   change expands the surface, coordinate affected owners and update the plan using existing
   authorization and review rules; preserve legal cross-component work.

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
- Acceptance: happy path + refusal path + reopen-safety; reader-older → typed refuse (the existing C4 state-schema contract, not a pack rule).
- Expected-change surface + evolution (planning, not a gate): C4 state functions and schema; C5 writes are not expected, and a legitimate need for one is coordinated with its owner and the plan updated; a second meaning of "hold" → candidate split; retire = keep-data read-only export (design §5).

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
dependency; a refusal-path test; a boundary test that a writer without authority over a
context's owned data is refused (the existing single-writer rule) — never a refusal of a
legitimate cross-context task.
**Explicit non-promises** `[DERIV]`: this does **not** eliminate agent context limits; does **not**
auto-fit any scale; is **not** a mandate for event sourcing, CQRS, microservices, or
one-process-per-context; does not make contexts permanent.

**Cost / counter-example**: packs cost writing and maintenance and can drift from code; premature
contexts can fragment a small codebase. Extra deployment, network latency and operations cost
apply when translation is a separately deployed service; an in-process ACL need not introduce
another process or network hop. Translation still has code and maintenance cost. Use only where an invariant or semantic gap justifies the cost.

**Bounded open questions**: (Q1) is KW truly *one* context or several (unread at source this
round)? (Q2) do VRPAI/CAD bridges expose a Published Language or an ad-hoc field set?
`[ASSUMPTION]` only. (Q3) do C4/C5 share one language (one context) or two? They share one state
store though design §3 lists them separately — resolve from source. (Q4) can the pack be validated
without a new gate (reuse the #268/#273 typed-result style as a component-scoped result)?

### 6b. Counter-examples and the low-ceremony path (complement, Grok `i279-ddd-counterexamples`)

Sources and verbatim quotes are in [i279-ddd-source-register.md](i279-ddd-source-register.md)
§ "Complement sources". Quotes were gathered by the complement worker; the Host spot-matched the
37signals and Shopify 2020 quotes live, the Vernon quotes remain worker-reported, and unreachable
pages are listed there.

**When DDD ceremony costs more than it returns** `[SRC]`: Fowler — "don't even consider
microservices unless you have a system that's too complex to manage as a monolith"; "even
experienced architects working in familiar domains have great difficulty getting boundaries right
at the beginning." Engineering cases: Shopify evolved into "a modular monolith" and Müller used
DDD *in-process* ("components as implementations of subdomains of the domain of commerce"), with
service splits kept for specific needs (high-throughput read-only use, data that "shouldn't flow
through other parts of the system"). 37signals: "we don't default to create services, actions,
commands, or interactors". These are deployment and layering choices of those teams, not DDD
requirements either way.

**Conditional low-ceremony options** `[DERIV]` — each applies only when its condition holds, none
is a universal DDD or KPR rule:

1. One codebase/process/database is a reasonable default *while* no measured scale, failure-domain
   or sealed-data need justifies a split; it does not forbid an existing justified process.
2. Prefer direct model operations over an added service/interactor layer *when* that layer would
   only add indirection; a domain service with a real cross-entity operation stays legitimate.
3. Introduce an aggregate *when* one transaction must protect a real business invariant.
4. Treat first-cut contexts as revisable; redraw on observed language/change-coupling evidence.
5. Keep one command within one consistency cluster *where* the invariant requires it; tasks may
   still span several (§5).

**Redesign patterns** (`[SRC]`; Vernon quotes worker-reported, Shopify Host spot-matched):

- *Giant aggregate, then split* — Vernon, Effective Aggregate Design Part I. **Illustrative
  fictional teaching case** (ProjectOvation, marked fictitious by its author): a Product
  aggregate holding all backlog items, releases and sprints caused concurrent-commit failures;
  the cause was "false invariants … artificial constraints imposed by developers".
- *Split drawn, then withdrawn* — same series, Part III (same fictional case): moving Task out of
  BacklogItem with eventual consistency was tried and superseded to avoid leaving "the true
  invariant unprotected".
- *Facades with no direction* — **engineering case**, Shopify (Müller 2020): interfaces "turned
  out to just be an added layer of indirection" while "every component depended on over half of
  all the other components."

_Research only. No root/Fable review claim; not a reopening of the B design._

---

## 7. Component-contract sketch for the optional DDD strategy component (Host, per user positioning)

This frames DDD as an installable/uninstallable strategy component in the converged core design — an optional extension, never a B0/migration precondition.

- **Responsibilities**: domain-modeling input to boundary decisions (vocabulary/invariant/change-rate evidence, never auto-partitioning); work-unit context-pack generation from existing records; mapping suggestions (marked ASSUMPTION where source unread); boundary-evolution recommendations with evidence. **Non-responsibilities**: no final value/architecture/acceptance judgment (Host/owner), no project management totality claim, no machine domain split.
- **Data ownership**: reads existing project records + versioned engineering documents. Generated domain maps, contract descriptions and packs should first reuse the project's existing versioned engineering documents and original evidence references. No new canonical `.kaola/` store, history ledger or authorization copy is introduced. A runtime artifact would require a separately justified contract, ownership and retention design.
- **Version compatibility**: an explicit version belongs to the optional pack contract. If this component cannot interpret a pack, it returns a component-scoped unsupported/unavailable result; core and unrelated authorized work continue. Optional-field tolerance is defined per contract, not globally.
- **Failure degradation / uninstall**: absent → work proceeds exactly as today (no pack is a gate); retire → the versioned pack documents simply remain in the project's Git, nothing else is removed; replacement is any equivalent pack producer behind the same pack schema.
- **Applicability criteria (when to install)**: multiple bounded languages or change-rates observed; invariant/consistency boundaries worth isolating; cross-context collaboration costing rework. **Simplified path**: single-context small projects use a one-paragraph vocabulary + invariants + expected-change note (the pack minus ceremony) — the counter-example rule (§6b) governs.
- **Validation design**: pack-vs-code drift check reusing existing suites (no new gate); one cross-edge contract test per dependency named in a pack; refusal-path test; boundary-evolution decisions cite observed evidence. Reuse the #268/#273 typed-result style as a component-scoped unsupported result, never a core gate (Q4 resolution proposal).

These are proposed component contract rows. Q1–Q3 are technical evidence questions, not mandatory Owner value choices. Actual adoption or a changed deployment commitment may require an Owner decision under existing scope; the already-authorized research and optional-component design do not require a new approval.


## Integration status — root corrections and complements (not implementation acceptance)

Integrated by the Host from main research @210b712e, the root-corrected draft and the two
complements. This records which review points the text now carries; it claims no Fable or root
acceptance.

Root technical review (six points): (1) an Agent work unit is not an aggregate (§5); (2) the three
KPR contexts and their core/supporting/generic labels are candidates needing product-value and
invariant evidence (§4); (3) cross-context transactions, shared/separate databases and a separate
ACL process are deployment choices, not DDD consequences (§3, §4, §6); (4) the expected-change
surface is planning information, not a global refusal, and an unsupported pack version degrades
only this component (§5, §7); (5) domain maps and packs reuse versioned Git engineering documents,
with no new `.kaola/` canonical store or authorization ledger (§7); (6) KW and VRPAI/CAD mappings
are unverified examples, and Q1–Q3 are technical evidence questions, not mandatory Owner
questions (§4, §6, §7).

The optional strategy interface can accept existing design/evidence references, a proposed task,
its acceptance surfaces and dependency contracts; it returns candidate boundary advice, a
versioned context-pack proposal, evidence gaps and a collaboration/verification plan. Agent
tasks may span domains; the Host/Owner retains value, architecture and acceptance judgments.
No output is an automatic permission gate or automatic task-graph rewrite.

Complements: [i279-ddd-contract-tests.md](i279-ddd-contract-tests.md) (per-contract tolerance;
existing suites are component-seam evidence, not proof of the proposed contexts; new fixtures are
described, not executed) and §6b (counter-examples as conditional options, fictional teaching
case vs engineering cases marked).

Bounded Fable review after this integration: assess the six corrected claims, remaining logical
contradictions, and the optional-component interface/failure/data boundaries. Do not reopen B0,
repeat source research, impose microservices, or convert technical evidence gaps into Owner
questions. Report substantive residual differences against the exact integrated commit.
