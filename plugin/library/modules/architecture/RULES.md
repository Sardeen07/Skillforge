---
module: architecture
capability: System design, architecture patterns and SOLID design
technologies:
applies: architecture, system design, design patterns, solid, microservices, monolith, scalability
checked_against: martinfowler.com, microservices.io, AWS Builders' Library
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## modular-monolith-first: Start with a modular monolith; split services for a concrete reason
tags: architecture, microservices, monolith, modular monolith, service boundaries, system design
keywords: should we use microservices
refs: https://martinfowler.com/bliki/MonolithFirst.html

Microservices add network failures, distributed transactions, deployment and observability costs. Start with one deployable organized into modules with explicit interfaces and no shared tables across modules; extract a service when a module needs independent scaling, deployment cadence, team ownership or isolation that the monolith cannot give.

## dependency-inversion: Depend on abstractions at boundaries (ports and adapters)
tags: architecture, dependency inversion, solid, hexagonal architecture, ports and adapters, clean architecture, testability
keywords: business logic imports database client
refs: https://alistair.cockburn.us/hexagonal-architecture/

Keep domain logic free of framework, database and HTTP code: define the interfaces it needs (ports) in the domain, and implement them in adapters at the edge. Dependencies point inward, so the core can be tested without infrastructure and adapters can change independently.

## single-responsibility: Give each module one reason to change
tags: architecture, single responsibility, solid, cohesion, coupling, modules, god class
keywords: class does everything, change ripples everywhere
refs: https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html

Group code that changes for the same reason and separate code that changes for different reasons (pricing rules vs. invoice rendering vs. persistence). A class or module that every feature touches is a sign responsibilities are mixed.

## composition-over-inheritance: Prefer composition to deep inheritance
tags: architecture, design patterns, composition, inheritance, liskov substitution, solid, strategy pattern
keywords: fragile base class, override breaks subclass
refs: https://en.wikipedia.org/wiki/Composition_over_inheritance

Deep inheritance hierarchies couple subclasses to base-class internals. Compose behavior from small objects behind interfaces (strategy, decorator), and when you do subclass, honor the Liskov substitution principle: a subclass must work anywhere the base type is expected, without strengthening preconditions.

## design-patterns-judiciously: Apply design patterns to solve present problems, not anticipated ones
tags: architecture, design patterns, factory, strategy, observer, over engineering, yagni
keywords: abstract factory for one class
refs: https://martinfowler.com/bliki/Yagni.html

Patterns name solutions to recurring forces; adding them before the force exists adds indirection without benefit. Introduce a strategy when you have two real variants, an observer when several consumers need events, a factory when construction logic is genuinely complex. Refactor toward patterns as needs appear.

## stateless-services-scaling: Keep application servers stateless to scale horizontally
tags: architecture, scalability, stateless, horizontal scaling, sessions, sticky sessions, system design
keywords: sticky sessions required, in memory session lost
refs: https://12factor.net/processes

Store sessions, uploads and caches that must be shared in external services (database, Redis, object storage), not in a process's memory or local disk, so any instance can serve any request and instances can be added, removed or restarted freely.

## event-driven-tradeoffs: Use events to decouple, and design for their failure modes
tags: architecture, event driven, message queue, pub sub, eventual consistency, coupling, event sourcing
keywords: hard to trace event flows
refs: https://martinfowler.com/articles/201701-event-driven.html

Events decouple producers from consumers but bring eventual consistency, duplicate and out-of-order delivery, and harder debugging. Version event schemas, include enough data for consumers (or an ID to fetch it), make consumers idempotent, trace events with correlation IDs, and keep synchronous calls where the caller needs the answer.

## data-ownership: Give each piece of data one owning service
tags: architecture, data ownership, shared database, microservices, bounded context, ddd
keywords: two services write the same table
refs: https://microservices.io/patterns/data/database-per-service.html

When several services write the same tables, schema changes require lockstep deploys and invariants have no owner. Assign each dataset a single owner that exposes it through an API or events; other services keep read models updated from those events if they need local copies.

## architecture-decision-records: Record significant decisions in ADRs
tags: architecture, adr, architecture decision records, documentation, tradeoffs, design review
keywords: why did we choose this
refs: https://adr.github.io/

Write a short decision record for choices that are costly to reverse (datastores, service boundaries, protocols): context, decision, alternatives considered and consequences. Keep ADRs in the repository next to the code so reviewers and future maintainers can see why.

## capacity-estimation: Estimate load and data growth before choosing an architecture
tags: architecture, system design, capacity planning, back of the envelope, scalability, throughput
keywords: will it scale
refs: https://sre.google/sre-book/software-engineering-in-sre/#intent-based-capacity-planning

Estimate requests per second at peak, read/write ratio, data size growth and latency targets with simple arithmetic before designing. A single well-indexed database handles far more than many designs assume; let numbers, not fashion, justify sharding, caching layers or queues, then load-test the critical path.

## strangler-fig-migration: Replace legacy systems incrementally with the strangler fig pattern
tags: architecture, legacy migration, strangler fig, rewrite, incremental, routing, refactoring
keywords: big bang rewrite, migrate monolith
refs: https://martinfowler.com/bliki/StranglerFigApplication.html

Avoid big-bang rewrites. Put a routing layer in front of the legacy system, move one capability at a time to the new implementation behind it, compare results in shadow mode where possible, and retire legacy paths as traffic moves. The system keeps working, and each step can be rolled back.
