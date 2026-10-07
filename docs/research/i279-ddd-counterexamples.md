# #279 complement: when DDD costs more than it returns

Fetched 2026-10-07. Complement only.

## Sources

Fowler, Microservice Premium, 13 May 2015: https://martinfowler.com/bliki/MicroservicePremium.html. Fowler, Monolith First, 3 Jun 2015: https://martinfowler.com/bliki/MonolithFirst.html. Westeinde, Shopify Engineering, 21 Feb 2019: https://shopify.engineering/blogs/engineering/deconstructing-monolith-designing-software-maximizes-developer-productivity. Müller, Shopify Engineering, 16 Sep 2020: https://shopify.engineering/shopify-monolith. Manrubia, 37signals Dev, 8 Nov 2022: https://dev.37signals.com/vanilla-rails-is-plenty/. Vernon, Part I and Part III, 2011: https://www.dddcommunity.org/wp-content/uploads/files/pdf_articles/Vernon_2011_1.pdf and https://www.dddcommunity.org/wp-content/uploads/files/pdf_articles/Vernon_2011_3.pdf.

Not reached. https://shopify.engineering/deconstructing-monolith-designing-software-that-maximizes-developer-productivity returned 404. https://vaughnvernon.com/ returned 403. https://vaughnvernon.co/ did not respond. No DDD Europe aggregate-redraw page was found (other talks only: https://2016.dddeurope.com/vaughn-vernon.html, https://2017.dddeurope.com/speakers/vaughn-vernon/). Vernon calls ProjectOvation fictitious.

## When it costs more than it returns

Fowler: "don't even consider microservices unless you have a system that's too complex to manage as a monolith." The premium is "automated deployment, monitoring, dealing with failure, eventual consistency".

Monolith First: "you shouldn't start a new project with microservices, even if you're sure your application will be big enough to make it worthwhile." "even experienced architects working in familiar domains have great difficulty getting boundaries right at the beginning." An early cut "brushes a layer of treacle" over the wrong line.

Shopify stayed one deployable. Westeinde: "We chose to evolve Shopify into a modular monolith". "no architecture is often the best architecture in the early days of a system." Müller used DDD in-process: "guided by the ideas of Domain Driven Design" and "components as implementations of subdomains of the domain of commerce". A service split "increases the overall complexity considerably." Exceptions: "a read-only use case with very high throughput" and data that "shouldn't flow through other parts of the system."

37signals dropped the kit. Manrubia: "We don't separate application-level and domain-level artifacts." "we don't default to create services, actions, commands, or interactors". He quotes Vernon: "Using Services overzealously will usually result in the negative consequences of creating an Anemic Domain Model". Basecamp 4: "400 controllers and 500 models" on a codebase "almost 9 years old."

Single-agent test: one person holds the model, and no measured invariant, second team, throughput split, or sealed data path forces a cut. Layers, an aggregate catalog, a context map, and a second process then cost more than they return.

## Checklist

1. One codebase, one process, one database.
2. No service or interactor layer. Call a model method.
3. No aggregate until one transaction must protect a real rule.
4. Do not freeze bounded contexts on the first design.
5. One command, one consistency cluster.
6. A second process only for scale, a separate failure domain, or sealed data.

## Patterns

1. Giant aggregate, then a split (Vernon, Part I). "Products have backlog items, releases, and sprints" became "a very large aggregate" holding "all BacklogItem, all Release, and all Sprint instances." "Bill plans a new BacklogItem and commits. The Product version is incremented to 2. Joe schedules a new Release and tries to save, but his commit fails because it was based on Product version 1." Cause: "false invariants in mind, not real business rules. These false invariants are artificial constraints imposed by developers." "We've solved the transaction failure issue by modeling it away."

2. Split drawn, then withdrawn (Vernon, Part III). Task was drawn outside BacklogItem and updated with eventual consistency. "Their various ideas are tried and then superseded." They kept Task inside, citing "the risk of leaving the true invariant unprotected, or allowing users to experience a possible stale status in the view." That split "remains in their hip pocket" if the aggregate is "larger than imagined."

3. Facades with no direction (Müller, 2020). Interfaces "turned out to just be an added layer of indirection". "every component depended on over half of all the other components."
