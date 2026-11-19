---
module: api-design
capability: HTTP and REST API design
technologies:
applies: api, rest, http, endpoint, status code, pagination, versioning
checked_against: RFC 9110 (HTTP Semantics), RFC 9457 (Problem Details), Google API design guide
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## http-method-semantics: Use HTTP methods by their semantics
tags: api design, rest, http methods, get, post, put, patch, delete, safe, idempotent
keywords: GET that deletes, POST for everything
refs: https://www.rfc-editor.org/rfc/rfc9110.html#name-method-definitions

GET and HEAD must be safe (no side effects), because caches, prefetchers and crawlers issue them freely. PUT and DELETE are idempotent: repeating them has the same effect. Use POST to create or for non-idempotent actions, PATCH for partial updates, and design URLs around resources (`/orders/123/cancel` as POST is acceptable for an action).

## status-codes-precise: Return precise status codes
tags: api design, http status codes, 400, 401, 403, 404, 409, 422, 429, error handling
keywords: 200 with error body, 500 for bad input
refs: https://www.rfc-editor.org/rfc/rfc9110.html#name-status-codes

Return 201 with a `Location` header on create, 204 for success with no body, 400/422 for invalid input, 401 when unauthenticated, 403 when authenticated but not allowed, 404 when missing (or hidden), 409 on state conflicts, 429 with `Retry-After` when rate limited, and 5xx only for server faults. Never return 200 with an error payload.

## problem-details-errors: Use a consistent machine-readable error format
tags: api design, error format, problem details, rfc 9457, validation errors, json
keywords: inconsistent error responses
refs: https://www.rfc-editor.org/rfc/rfc9457.html

Return errors as `application/problem+json` with `type`, `title`, `status`, `detail`, plus extension fields such as a list of invalid fields and a request/trace ID. A single format lets clients handle errors generically. Never include stack traces or internal identifiers.

## pagination-cursor: Paginate collections with cursors and a bounded page size
tags: api design, pagination, cursor, limit, offset, next link, large collections
keywords: returns all rows, page drift
refs: https://cloud.google.com/apis/design/design_patterns#list_pagination

Every list endpoint should be paginated from day one with a maximum page size. Prefer opaque cursor tokens (`?page_token=...` returning `next_page_token`) over offsets: they stay stable as data changes and map to efficient keyset queries. Document the default sort order.

## idempotency-keys: Accept idempotency keys on non-idempotent writes
tags: api design, idempotency, idempotency key, retries, duplicate requests, payments, post
keywords: double charge on retry
refs: https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/

Clients retry after timeouts without knowing whether the first request succeeded. For POSTs with side effects (payments, orders), accept an `Idempotency-Key` header, store the key with the result under a unique constraint, and replay the stored response for repeats with the same key (reject the same key with a different body).

## versioning-compatibility: Evolve APIs compatibly and version only for breaking changes
tags: api design, versioning, backward compatibility, breaking change, deprecation, contract
keywords: renamed field broke clients
refs: https://cloud.google.com/apis/design/compatibility

Adding optional fields, endpoints and enum values is compatible (if clients are told to ignore unknown values); removing or renaming fields, changing types or tightening validation is breaking. Ship breaking changes under a new version (`/v2` or a header), announce deprecations with the `Deprecation`/`Sunset` headers, and keep the old version running for a stated period.

## input-validation-boundary: Validate requests strictly against a published schema
tags: api design, validation, openapi, json schema, input validation, security, contract
keywords: unknown fields accepted, mass assignment
refs: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html

Describe the API in OpenAPI and validate every request against it (types, formats, lengths, ranges, enums). Reject or ignore unknown fields deliberately, never bind request bodies directly to database models, and set maximum body sizes.

## rate-limiting-api: Rate-limit by client and communicate limits
tags: api design, rate limiting, throttling, 429, retry after, abuse, quotas
keywords: one client overloads api
refs: https://www.rfc-editor.org/rfc/rfc6585.html#section-4

Apply per-client (API key, user, IP) limits with a token bucket or sliding window kept in a shared store, return 429 with `Retry-After`, and expose remaining quota in headers (`RateLimit-*`). Limit expensive endpoints and authentication attempts more tightly.

## timeouts-and-long-operations: Model long operations as jobs instead of long requests
tags: api design, long running operation, async api, 202 accepted, polling, webhooks, timeout
keywords: request times out after 30 seconds
refs: https://cloud.google.com/apis/design/design_patterns#long_running_operations

Requests that take longer than a few seconds will hit proxy and client timeouts. Return `202 Accepted` with an operation resource the client can poll (`GET /operations/{id}`) or a webhook callback, and make the job itself idempotent and retryable.

## filtering-and-sparse-fields: Support filtering and field selection without exposing internals
tags: api design, filtering, sorting, sparse fieldsets, over fetching, query parameters
keywords: arbitrary sort column, sql injection in sort
refs: https://jsonapi.org/format/#fetching-sparse-fieldsets

Offer explicit filter and sort parameters mapped through an allowlist to indexed columns, never raw SQL fragments or arbitrary field names. Field selection (`?fields=id,name`) reduces payloads for mobile clients; keep defaults small.

## webhook-signature-verification: Verify webhook signatures over the raw body with a replay window
tags: api design, webhooks, hmac, signature verification, replay attack, timestamp, stripe
keywords: verify webhook, signature header, x-signature
refs: https://docs.stripe.com/webhooks#verify-events

Compute the HMAC over the exact raw request body (not re-serialized JSON) plus the signed timestamp, compare with `hmac.compare_digest`, and reject events whose timestamp is outside a short tolerance (e.g. 5 minutes) so captured requests cannot be replayed. Process each event id once, since providers retry deliveries.

## webhook-delivery: Deliver outgoing webhooks asynchronously with retries and signatures
tags: api design, webhooks, delivery, retries, queue, signing secret, idempotency
keywords: sending webhooks to customers
refs: https://www.standardwebhooks.com/

Send webhooks from a background queue, never inline in the request that triggered them; sign each payload with a per-endpoint secret and timestamp, include a unique event id for receiver deduplication, retry with exponential backoff over hours, and disable endpoints that keep failing after notifying their owner.

## conditional-requests-etags: Use ETags for caching and optimistic concurrency
tags: api design, etag, if none match, if match, 304, 412, caching, concurrency
keywords: lost update via api, clients refetch unchanged data
refs: https://www.rfc-editor.org/rfc/rfc9110.html#name-conditional-requests

Return an `ETag` for resources; honor `If-None-Match` with `304 Not Modified` to save bandwidth, and require `If-Match` on updates, answering `412 Precondition Failed` when the resource changed since the client read it. This prevents lost updates between concurrent API clients.
