---
module: graphql
capability: GraphQL schema design, performance and security
technologies: graphql
applies: graphql, resolver, schema, apollo, dataloader, mutation
checked_against: graphql.org best practices and GraphQL over HTTP specification
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## dataloader-batching: Batch resolver lookups with DataLoader
tags: graphql, dataloader, n+1, resolvers, batching, performance, database
keywords: one query per item in list
refs: https://graphql.org/learn/performance/#the-n1-problem

Field resolvers run per object, so `posts { author { name } }` issues one author query per post. Use a per-request DataLoader that batches keys within a tick into one `WHERE id IN (...)` query and caches results for that request. Create loaders per request so caches never leak between users.

## query-cost-limits: Limit query depth, complexity and size
tags: graphql, query depth, complexity, denial of service, security, persisted queries, introspection
keywords: deeply nested query takes server down
refs: https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html

A single nested query can request millions of objects. Enforce maximum depth and a cost/complexity budget, cap list arguments (`first: Int` with a maximum), set timeouts, and for first-party clients accept only persisted (allowlisted) queries. Disable introspection in production if the schema is not public.

## field-level-authorization: Authorize in resolvers or the business layer, per field and object
tags: graphql, authorization, resolvers, security, field level, idor, context
keywords: user queried other users data via nested field
refs: https://graphql.org/learn/authorization/

Every path to an object must enforce authorization: a type reachable through several parent fields is easy to leak through one of them. Put checks in the business/data layer that resolvers call (with the user from request context), not only at the top-level query.

## nullable-and-errors: Design nullability deliberately and return errors as data where expected
tags: graphql, nullability, errors, schema design, union types, partial results
keywords: whole query null because one field failed
refs: https://graphql.org/learn/best-practices/#nullability

A non-null field that errors nulls its parent, cascading upward. Make fields nullable where failure is plausible (cross-service data), and model expected business errors as part of the schema (a `union CreateOrderResult = Order | ValidationError`) rather than only top-level `errors`.

## mutation-input-payload: Use input types and payload types for mutations
tags: graphql, mutations, input types, payload, schema evolution, client cache
keywords: many scalar arguments
refs: https://graphql.org/learn/mutations/

Give each mutation a single `input` argument of a dedicated input type and return a payload type containing the changed object(s) and any user errors. This lets you add fields without breaking clients and lets client caches update from the returned objects.

## connections-pagination: Paginate lists with connections and enforce maximum page size
tags: graphql, pagination, connections, cursor, relay, edges, first after
keywords: list field returns everything
refs: https://graphql.org/learn/pagination/

Expose large lists as cursor-based connections (`first`/`after` returning `edges`, `pageInfo { endCursor hasNextPage }`) with a server-enforced maximum `first`, instead of unbounded list fields.

## schema-evolution-deprecation: Evolve the schema additively and deprecate before removal
tags: graphql, schema evolution, deprecated, breaking changes, versioning, field usage
keywords: removed field broke mobile app
refs: https://graphql.org/learn/best-practices/#versioning

GraphQL APIs are usually unversioned: add fields and types freely, mark old fields `@deprecated(reason: "Use fullName")`, track field usage from operation logs, and remove only after clients have migrated. Run a schema diff check in CI to catch breaking changes.
