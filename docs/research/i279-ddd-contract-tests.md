# #279 COMPLEMENT — contract verification for the work-unit context pack

Complements i279-ddd-method.md. URLs fetched 2026-10-07; all reachable.

## Primary sources (verbatim)

- **Robinson/Fowler, consumerDrivenContracts** (martinfowler.com/articles/consumerDrivenContracts.html): "we build services that share contracts, not types." "A consumer-driven contract is closed and complete with respect to the entire set of functionality demanded of it by its existing consumers." Unit tests "assert each expectation … in a repeatable, automated fashion with each build."
- **Fowler, TolerantReader** (martinfowler.com/bliki/TolerantReader.html): "be conservative in what you do, be liberal in what you accept from others." Send the provider "the reader and its tests … to detect potential breakages."
- **Pact docs** (docs.pact.io, /getting_started/how_pact_works): "Contract testing is a technique for testing an integration point by checking each application in isolation to ensure the messages it sends or receives conform to a shared understanding." "only parts of the communication that are actually used by the consumer(s) get tested" — "contract by example". Verification: actual response "compared with the minimal expected response … passes if each request generates a response that contains at least the data described."
- **Spring Modulith 2.1.1** (docs.spring.io/spring-modulith/reference/verification.html): `ApplicationModules.of(...).verify()` — "No cycles on the application module level"; "Efferent module access via API packages only"; "Explicitly allowed application module dependencies only". No literal `ApplicationModuleVerifier` exists in current docs; entry point is `verify()`.
- **JSON Schema** (json-schema.org/understanding-json-schema/reference/schema; /draft/2020-12/release-notes): "A version of JSON Schema is called a dialect." "$schema … declare which dialect of JSON Schema the schema was written for"; versionless `schema#` "has since been deprecated"; "Meta-data keywords are the most interoperable because they don't affect validation."
- **Fowler test-pyramid** (martinfowler.com/articles/practical-test-pyramid.html): "Automated contract tests … serve as a good regression test suite." CDC: "consumers of an interface write tests that check the interface for all data they need … The providing team runs the CDC tests continuously and keeps them green / Both teams talk to each other once the CDC tests break."

## Existing KPR suites: component-seam contract evidence

These suites verify real interfaces between existing components. They do not establish that the
candidate DDD bounded contexts of i279-ddd-method.md §4 are real; that still needs language,
invariant and change-coupling evidence.

- **test-issue-273-list-identity** — consumer test over real C1 entry (`kaola-acp.py list`): identity dispositions, `agent_alive` never leaked on non-bool. `ConsumerSeatProjection` adds C5's contract over C1 rows: `unbound-live-row:` → `occupancy_unknown`, never released; input bytes unchanged (tolerant read); wrong-expectation control proves the oracle bites.
- **test-issue-244-dispatch + holder-prompt-binding** — C5→C1 seam: fake-Runner receipts at the real subprocess boundary; `resolved-not-applied` decoys assert advertised≠applied; `applied: unknown` never blocks send (tolerant reader); `--expected-holder-instance-id` binds send to exact holder.
- **test-issue-274-package-closure** — Modulith `verify()` analog (C7→C6): isolated package contains the helper, runs the real recovery path; removal fails naming the dependency — no hidden fallback; `signal-unverified` typed refusals.
- **#271 chain receipts** — live CDC chain: execute → original `dispatch_event_cursor` → collect bound to it → rotated range honestly reports `event-range-unavailable` (typed gap; "silent gap loss is forbidden", design §6) → exact-stop. Partial evidence only (correction aa1c1444): the original cursor-8 collect range was unavailable and failure/permission coverage is unknown, so this is not a PASS of the original chain.

## One NEW contract test per context-edge (described fixtures — proposed, NOT executed)

Neither fixture exists or has run; they are design descriptions only.

- **C4→C5 dispositions**: fixture writes C4-owned `kaola-heartbeat-prompt/2` doc (grants + dispatch_links + task at rev N), runs real `execute`: expect `kaola-dispatch-index/1` rows; typed `requirement-unmet`/`resource-conflict`/`shared-occupied` on unmet links; rev conflict → `conflict`, no partial write; extra-field handling follows each schema's own stated rule (e.g. a reader may ignore unknown optional/meta fields where that schema says so), while authorization, grant, writer and other permission- or write-bearing fields are never tolerated when unknown or malformed — no blanket "unknown extra fields ignored"; `retire-unmet` propagated unchanged.
- **C1→C3 event cursor**: fixture drives send→observe with controlled seqs: expect `dispatch_event_cursor` on the receipt; dedup by `(source_holder, source_epoch, seq)` under at-least-once replay; rotated range → typed gap/`event-range-unavailable`, never fabricated coverage; `truncated` flagged.

## Pack drift — reuse, no new gate

A pack's "dependency contracts" names seams that already own suites; drift check = `validate.sh --suite <basename>` on those names (explicit-subset mechanism). An unsupported pack `contract-version` yields a component-scoped unsupported result (ADR-3 typed style) for the optional DDD component only; core and unrelated authorized work continue. A seam without a suite is a coverage finding → write one consumer-side fixture as above — never a new gate.
