---
module: distributed-systems
capability: Distributed systems, caching and background jobs
technologies:
applies: distributed, microservices, cache, queue, retry, background job, idempotency, scalability
checked_against: AWS Builders' Library, Google SRE book, Martin Kleppmann's Designing Data-Intensive Applications
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## timeouts-everywhere: Set a timeout on every network call
tags: distributed systems, timeouts, network calls, resilience, cascading failure, http client
keywords: request hangs forever, threads exhausted
refs: https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/

A remote call without a timeout can hold a thread, connection or request forever, and one slow dependency then exhausts the caller. Set connect and request timeouts on every client (HTTP, database, cache, queue), derived from the dependency's latency percentiles, and propagate a deadline so downstream calls do not outlive the original request.

## retries-backoff-jitter: Retry only transient failures, with capped exponential backoff and jitter
tags: distributed systems, retries, exponential backoff, jitter, retry storm, transient errors
keywords: retry immediately in loop, thundering herd
refs: https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/, https://www.rfc-editor.org/rfc/rfc9110.html#name-retry-after

Retry only idempotent operations and only on transient errors (timeouts, 503, 429, connection resets), with exponential backoff plus random jitter and a small maximum number of attempts. Retry at one layer only: retries at every layer multiply load during an outage. Respect `Retry-After`, which servers send either as seconds (`120`) or as an HTTP date (`Wed, 21 Oct 2026 07:28:00 GMT`); parse both (RFC 9110 §10.2.3).

## idempotent-consumers: Make message and job handlers idempotent
tags: distributed systems, idempotency, at least once delivery, duplicate messages, queue, consumers
keywords: message processed twice, duplicate emails
refs: https://microservices.io/patterns/communication-style/idempotent-consumer.html

Queues and job systems deliver at least once, so the same message can be handled twice. Record processed message IDs (or use a natural key with a unique constraint) in the same transaction as the side effect, and make handlers check before acting. "Exactly once" is achieved by idempotency, not by the broker.

## transactional-outbox: Publish events with an outbox, not dual writes
tags: distributed systems, outbox pattern, events, dual write, consistency, kafka, message broker
keywords: saved to db but event not sent
refs: https://microservices.io/patterns/data/transactional-outbox.html

Writing to the database and then publishing to a broker can fail between the two, leaving them inconsistent. Insert the event into an `outbox` table in the same transaction as the state change, and have a relay (polling or change-data-capture) publish it and mark it sent. Consumers must still be idempotent.

## cache-aside-invalidation: Use cache-aside with TTLs and explicit invalidation
tags: caching, cache aside, ttl, invalidation, stale data, redis, consistency
keywords: users see old data after update
refs: https://docs.aws.amazon.com/whitepapers/latest/database-caching-strategies-using-redis/caching-patterns.html

Read from the cache, fall back to the source and populate on miss, and on write update the source then delete (not update) the cache key. Always set a TTL so missed invalidations heal. Include a version in keys when the cached shape changes, and never cache per-user data under a shared key.

## cache-stampede: Prevent cache stampedes on hot keys
tags: caching, cache stampede, thundering herd, dogpile, request coalescing, hot key, ttl jitter
keywords: database spikes when cache expires
refs: https://en.wikipedia.org/wiki/Cache_stampede

When a hot key expires, every request misses at once and hits the database. Coalesce concurrent misses (single-flight or a short lock so one request recomputes), add random jitter to TTLs so keys do not expire together, and serve stale values while refreshing in the background for keys that tolerate it.

## circuit-breaker-bulkhead: Isolate failing dependencies with circuit breakers and bulkheads
tags: distributed systems, circuit breaker, bulkhead, resilience, graceful degradation, fallback
keywords: one slow service takes everything down
refs: https://martinfowler.com/bliki/CircuitBreaker.html

After repeated failures, stop calling a dependency for a cooldown period and fail fast or serve a fallback; probe with limited requests before closing again. Give each dependency its own bounded pool or concurrency limit (bulkhead) so one failure cannot consume all threads or connections.

## background-job-design: Keep jobs small, retryable and observable
tags: background jobs, task queue, workers, retries, dead letter queue, scheduling, celery, sidekiq
keywords: job stuck, long job lost on deploy
refs: https://aws.amazon.com/builders-library/avoiding-insurmountable-queue-backlogs/

Pass identifiers rather than large payloads, split long work into resumable chunks with checkpoints, set per-job timeouts, retry with backoff, and route repeatedly failing jobs to a dead-letter queue that someone monitors. Alert on queue depth and age of the oldest message, not just errors.

## backpressure-load-shedding: Bound queues and shed load before collapsing
tags: distributed systems, backpressure, load shedding, queue limits, overload, 503, capacity
keywords: latency grows until everything times out
refs: https://aws.amazon.com/builders-library/using-load-shedding-to-avoid-overload/

Unbounded in-memory queues turn overload into ever-growing latency and out-of-memory crashes. Bound queues and concurrency, reject excess work early with 429/503 (cheaply, before doing expensive work), and prioritize critical traffic. Autoscaling helps only if it reacts faster than the queue grows.

## consistency-models: Choose the consistency each operation needs and design for it
tags: distributed systems, eventual consistency, strong consistency, read your writes, replication lag, replicas
keywords: user does not see their own update, read replica stale
refs: https://jepsen.io/consistency

Reads from replicas or caches can be stale. For flows where a user must see their own write (after saving a profile), read from the primary or track a write timestamp/LSN; elsewhere accept eventual consistency explicitly and design the UI for it. Use the database's transactions and constraints for invariants rather than application-level checks across services.
