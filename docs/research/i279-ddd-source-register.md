# Source register — issue #279 DDD research (fetched 2026-10-07)

Every URL fetched, fetch date, and the verbatim quotes used in
[i279-ddd-method.md](i279-ddd-method.md). All fetches were read-only. Quotes are exact as returned by the
fetch (markdown view); ellipses `…` mark elision, quotes are otherwise contiguous.

## Successfully fetched

### 1. https://martinfowler.com/bliki/BoundedContext.html — 2014-01-15; fetched 2026-10-07
- "Bounded Context is a central pattern in Domain-Driven Design. It is the focus of DDD's strategic design section which is all about dealing with large models and teams."
- "total unification of the domain model for a large system will not be feasible or cost-effective"

### 2. https://martinfowler.com/bliki/UbiquitousLanguage.html — 2006-10-31; fetched 2026-10-07
- "Ubiquitous Language is the term Eric Evans uses in Domain Driven Design for the practice of building up a common, rigorous language between developers and users."
- (Evans quote inside) "Domain experts should object to terms or structures that are awkward or inadequate to convey domain understanding; developers should watch for ambiguity or inconsistency that will trip up design."

### 3. https://martinfowler.com/bliki/DDD_Aggregate.html — 2013-04-23; fetched 2026-10-07
- "An aggregate will have one of its component objects be the aggregate root. Any references from outside the aggregate should only go to the aggregate root."
- "Aggregates are the basic element of transfer of data storage - you request to load or save whole aggregates. Transactions should not cross aggregate boundaries."

### 4. https://martinfowler.com/bliki/ValueObject.html — 2016-11-14; fetched 2026-10-07
- "Objects that are equal due to the value of their properties, in this case their x and y coordinates, are called value objects."
- "value objects should be immutable"

### 5. https://martinfowler.com/eaaDev/DomainEvent.html — 2005-12-12; fetched 2026-10-07
- "The essence of a Domain Event is that you use it to capture things that can trigger a change to the state of the application you are developing."
- "it's important that this source data is immutable. That is once you've created the event object this source data cannot be changed."

### 6. https://martinfowler.com/eaaCatalog/repository.html — PoEAA, 2003-03-05; fetched 2026-10-07
- "A Repository mediates between the domain and data mapping layers, acting like an in-memory domain object collection."
- "Repository also supports the objective of achieving a clean separation and one-way dependency between the domain and data mapping layers."

### 7. https://martinfowler.com/bliki/EvansClassification.html — 2005-12-14; fetched 2026-10-07
- "Entity: Objects that have a distinct identity that runs through time and different representations."
- "Value Object: Objects that matter only as the combination of their attributes. Two value objects with the same values for all their attributes are considered equal."
- "Service: A standalone operation within the context of your domain."

### 8. https://martinfowler.com/bliki/MonolithFirst.html — 2015-06-03; fetched 2026-10-07
- "you shouldn't start a new project with microservices, even if you're sure your application will be big enough to make it worthwhile."
- "they only work well if you come up with good, stable boundaries between the services - which is essentially the task of drawing up the right set of BoundedContexts."

### 9. https://martinfowler.com/bliki/MicroservicePremium.html — 2015-05-13; fetched 2026-10-07
- "don't even consider microservices unless you have a system that's too complex to manage as a monolith."
- "The majority of software systems should be built as a single monolithic application. Do pay attention to good modularity within that monolith, but don't try to separate it into separate services."

### 10. https://martinfowler.com/articles/microservices.html — Lewis & Fowler, 2014-03-25; fetched 2026-10-07
- "At a first approximation, we can observe that services map to runtime processes, but that is only a first approximation."
- "Microservices prefer letting each service manage its own database, either different instances of the same database technology, or entirely different database systems - an approach called Polyglot Persistence."
- "If you find yourself repeatedly changing two services together, that's a sign that they should be merged."
- "The downside is that you have to worry about changes to one service breaking its consumers."

### 11. https://martinfowler.com/articles/consumerDrivenContracts.html — Ian Robinson, 2006-06-12; fetched 2026-10-07
- "we build services that share contracts, not types."
- "Loosely-coupled services are relatively independent of one another, but remain coupled nonetheless. What the pattern does do, however, is excavate and put on display some of those residual, 'hidden' couplings, so that providers and consumers can better negotiate and manage them."

### 12. https://martinfowler.com/bliki/TolerantReader.html — 2011-05-09; fetched 2026-10-07
- "be conservative in what you do, be liberal in what you accept from others." (Postel's Law, quoted by Fowler)
- "My recommendation is to be as tolerant as possible when reading data from a service."

### 13. https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/ddd-oriented-microservice — ms.date 2021-01-13; fetched 2026-10-07
- "It describes independent problem areas as Bounded Contexts (each Bounded Context correlates to a microservice), and emphasizes a common language to talk about these problems."
- "an entity could be loaded from the database… the domain model entity classes should be POCOs."
- (Evans via MS) "Domain Model Layer: Responsible for representing concepts of the business, information about the business situation, and business rules."

### 14. https://learn.microsoft.com/en-us/dotnet/architecture/microservices/architect-microservice-container-applications/identify-microservice-domain-model-boundaries — 2018-09-20; fetched 2026-10-07
- "A domain model with specific domain entities applies within a concrete BC or microservice. A BC delimits the applicability of a domain model…"
- "the most important thing is that you shouldn't try to unify the terms. Instead, accept the differences and richness provided by each domain."

### 15. https://learn.microsoft.com/en-us/azure/architecture/microservices/model/domain-analysis — ms.date 2026-02-23; fetched 2026-10-07
- "DDD has a strategic phase and a tactical phase. In strategic DDD, you define the large-scale system structure. Strategic DDD ensures that your architecture remains focused on business capabilities. Tactical DDD provides design patterns that you can use to create the domain model."
- "Core subdomains provide a competitive advantage." / "Supporting subdomains keep the business operational but don't differentiate it from competitors." / "Generic subdomains represent problems that the industry already solved."
- "Bounded contexts aren't necessarily isolated from one another."
- (relationship list) "Customer-Supplier… Open Host Service and Published Language… Anti-corruption Layer… Separate Ways"

### 16. https://learn.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer — ms.date 2026-05-28; fetched 2026-10-07
- "Isolate the different subsystems by placing an anti-corruption layer between them. This layer translates communication between the two systems."
- "Eric Evans first described this pattern in *Domain-Driven Design: Tackling Complexity in the Heart of Software*."
- "This pattern might not be suitable when: The new and legacy systems have no significant semantic differences."

### 17. https://www.infoq.com/articles/ddd-contextmapping/ — Alberto Brandolini, 2009-11-25; fetched 2026-10-07
- "This is not a precise well-defined UML diagram: it's a working tool that allows us to map a fuzzy situation, so a somewhat fuzzy look is necessary."
- "an upstream context will influence the downstream counterpart while the opposite might not be true."

### 18. https://docs.spring.io/spring-modulith/reference/ — Spring Modulith 2.1.1; fetched 2026-10-07
- "Spring Modulith is an opinionated toolkit to build domain-driven, modular applications with Spring Boot."

### 19. https://docs.spring.io/spring-modulith/reference/fundamentals.html — Spring Modulith 2.1.1; fetched 2026-10-07
- "an application module is a unit of functionality that consists of the following parts: An API exposed to other modules… Internal implementation components that are not supposed to be accessed by other modules… References to API exposed by other modules… usually referred to as *required interface*."
- "It allows them to apply structural validation, document the module arrangement, run integration tests for individual modules, observe the modules' interaction at runtime…"

### 20. https://www.domainlanguage.com/ddd/ — Eric Evans' official DDD resources; fetched 2026-10-07
- "Domain-Driven Design, by Eric Evans, provides a broad framework for making design decisions and a vocabulary for discussing domain design."
- (DDD Reference) "This reference guide provides a quick and authoritative summary of the key concepts of Domain-Driven Design."

### 21. https://www.informit.com/store/implementing-domain-driven-design-9780133039894 — Vaughn Vernon, Addison-Wesley, published 2013-02-06; fetched 2026-10-07
- "Vaughn Vernon couples guided approaches to implementation with modern architectures, highlighting the importance and value of focusing on the business domain while balancing technical considerations."
- Table of contents (verbatim chapter/section identifiers used in the method): "Chapter 2: Domains, Subdomains, and Bounded Contexts"; "Chapter 3: Context Maps"; "Chapter 10: Aggregates … Rule: Model True Invariants in Consistency Boundaries"; "Chapter 12: Repositories".

### 22. https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/microservices-on-aws.html — AWS, pub. 2023-07-31; fetched 2026-10-07
- "Deciding between microservices or monoliths should be made on a case-by-case basis, considering factors like scale, complexity, and specific use cases."
- "While microservices offer many benefits, it's vital to assess your use case's unique requirements and associated costs. Monolithic architecture or alternative approaches may be more appropriate in some cases."

### 23. https://vaughnvernon.com/ — Vaughn Vernon official site; fetched 2026-10-07
- "I am a software ecologist*, architect, modeler, and optimizer of teams and individuals… championing simplicity in the face of complexity."
- Confirms authorship/series of IDDD and *Strategic Monoliths and Microservices*; no quotable definitional text (redirect to publishing pages).

## Attempted, unreachable (recorded for coverage honesty; fetched 2026-10-07)

- https://martinfowler.com/bliki/ContextMap.html — HTTP 404 (no Fowler bliki; context map covered by Evans/Vernon/Brandolini instead).
- https://martinfowler.com/bliki/AntiCorruptionLayer.html — HTTP 404 (ACL sourced from Evans/Microsoft/Azure instead).
- https://www.informit.com/articles/article.aspx?p=1930561 — redirected to the InformIT articles index; no Vernon chapter body returned (IDDD ToC used from the store page, item 21).
- https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/welcome.html — HTTP 404.
- https://modulithics.com/ — transport error.
- https://modulithics.dev/ — transport error. (Kieran Scott / "modulithics" not reachable this round.)
- `websearch` tool: repeatedly returned "Web search cancelled"; no search-result URLs are cited.

## Non-web (in-repo) sources used for the mapping, marked `[DERIV]`/`[SRC: in-repo]`
- `docs/designs/modular-core-2026-10-07/design.md` @ `889f12bbf80441d7013f8b92349f37a42798df00` (C1–C8, contracts, subtraction, §6a write-owner table).
- `docs/designs/modular-core-2026-10-07/adr.md` @ same commit (ADR-3 refuse versions; ADR-7 KW optional module / dual digest).
- `docs/research/modular-architecture-and-unified-data-2026-10-07.md` (KW multi-writer + resumable step-receipt workflows + dual digest; §3).
- `kaola-project-runner` AGENTS.md (owner rules: no authorization-history/tombstone bookkeeping; no auto-adoption).
- KW repo (`~/Workspace/kaola-workflow`): read-only, referenced only via the in-repo records above; KW source not re-opened for this note.

## Complement sources (Grok `i279-ddd-counterexamples`, fetched 2026-10-07)

Gathered by the complement worker; quotes as it returned them. Host spot-check 2026-10-07 by exact
string match on the live page: 37signals ("default to create services, actions, commands, or
interactors") and Shopify 2020 ("just be an added layer of indirection") matched; the Vernon Part I
PDF returned HTTP 200 but its text was not extracted here, so its quotes remain worker-reported. Used in
i279-ddd-method.md §6b.

- Fowler, Microservice Premium (#9) and Monolith First (#8): "you shouldn't start a new project with microservices, even if you're sure your application will be big enough to make it worthwhile."; "even experienced architects working in familiar domains have great difficulty getting boundaries right at the beginning."
- https://shopify.engineering/blogs/engineering/deconstructing-monolith-designing-software-maximizes-developer-productivity — Westeinde, 2019-02-21 (**engineering case**): "We chose to evolve Shopify into a modular monolith"; "no architecture is often the best architecture in the early days of a system."
- https://shopify.engineering/shopify-monolith — Müller, 2020-09-16 (**engineering case**): "guided by the ideas of Domain Driven Design"; "components as implementations of subdomains of the domain of commerce"; a service split "increases the overall complexity considerably"; exceptions "a read-only use case with very high throughput" and data that "shouldn't flow through other parts of the system"; interfaces "turned out to just be an added layer of indirection"; "every component depended on over half of all the other components."
- https://dev.37signals.com/vanilla-rails-is-plenty/ — Manrubia, 2022-11-08 (**engineering case**): "We don't separate application-level and domain-level artifacts."; "we don't default to create services, actions, commands, or interactors"; quoting Vernon: "Using Services overzealously will usually result in the negative consequences of creating an Anemic Domain Model".
- https://www.dddcommunity.org/wp-content/uploads/files/pdf_articles/Vernon_2011_1.pdf and https://www.dddcommunity.org/wp-content/uploads/files/pdf_articles/Vernon_2011_3.pdf — Vernon, Effective Aggregate Design Parts I/III, 2011 (**illustrative fictional teaching case**: ProjectOvation, called fictitious by the author): "false invariants in mind, not real business rules. These false invariants are artificial constraints imposed by developers."; "the risk of leaving the true invariant unprotected, or allowing users to experience a possible stale status in the view."
- Unreachable for this worker: https://shopify.engineering/deconstructing-monolith-designing-software-that-maximizes-developer-productivity (404); https://vaughnvernon.com/ (403 on this fetch, although #23 above was fetched earlier the same day); https://vaughnvernon.co/ (no response); no DDD Europe aggregate-redraw page found.
