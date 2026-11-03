---
module: redis
capability: Redis caching, data structures and operations
technologies: redis
applies: redis, cache, ttl, rate limit, pub sub, session store
checked_against: Redis 7.4 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## ttl-on-cache-keys: Set a TTL on every cache key and an eviction policy
tags: redis, ttl, expire, eviction policy, maxmemory, cache, memory
keywords: redis out of memory, keys never expire
refs: https://redis.io/docs/latest/develop/reference/eviction/

Write cache entries with an expiry (`SET key value EX 300`) and configure `maxmemory` with an eviction policy (`allkeys-lru` or `allkeys-lfu` for pure caches; `volatile-*` when Redis also stores data that must not be evicted). Without them memory grows until writes fail.

## avoid-keys-command: Never use KEYS or unbounded commands in production
tags: redis, keys command, scan, blocking, latency, single threaded, performance
keywords: redis latency spike, KEYS *
refs: https://redis.io/docs/latest/commands/keys/

Redis executes commands on one thread, so `KEYS *`, `SMEMBERS` on huge sets, `HGETALL` on huge hashes or `DEL` of a huge key block every client. Use `SCAN`/`SSCAN`/`HSCAN` with cursors, `UNLINK` for asynchronous deletion, and keep collections bounded.

## pipelining-batching: Pipeline or batch many small commands
tags: redis, pipelining, mget, round trips, latency, batch, performance
keywords: thousands of GET calls slow
refs: https://redis.io/docs/latest/develop/use/pipelining/

Each command costs a network round trip. Send many independent commands in a pipeline, or use multi-key commands (`MGET`, `MSET`, `HMGET`). In Redis Cluster, multi-key commands require all keys in one hash slot (use hash tags like `{user:42}`).

## atomic-operations-lua: Use atomic commands or Lua for read-modify-write
tags: redis, atomicity, incr, lua script, transactions, race condition, watch
keywords: get then set race
refs: https://redis.io/docs/latest/develop/interact/programmability/eval-intro/

`GET` followed by `SET` from the client races with other clients. Use atomic commands (`INCR`, `HINCRBY`, `SET NX EX`, `GETDEL`) or a Lua script/function for multi-step logic; scripts run atomically. `MULTI/EXEC` batches commands but does not let you branch on values read inside it.

## distributed-lock-caveats: Use Redis locks with expiry, unique tokens and fencing
tags: redis, distributed lock, set nx, redlock, lock expiry, fencing token, concurrency
keywords: two workers held the lock
refs: https://redis.io/docs/latest/develop/use/patterns/distributed-locks/

Acquire with `SET lock:key <random-token> NX PX 30000` and release only if the token matches (a Lua compare-and-delete). Locks can expire while the holder is paused, so for correctness-critical work also use a fencing token checked by the resource (for example a version column in the database); for efficiency-only locks a single instance is fine.

## rate-limiting-redis: Implement rate limits with atomic counters or sliding windows
tags: redis, rate limiting, sliding window, token bucket, incr, expire, sorted set
keywords: rate limiter race condition
refs: https://redis.io/glossary/rate-limiting/

A fixed window is `INCR key` plus `EXPIRE key window NX` (Redis 7) in one pipeline or script. For smoother limits use a sliding-window log in a sorted set (`ZADD`, `ZREMRANGEBYSCORE`, `ZCARD` in one Lua script) or a token bucket script. Key by user or API key, not only IP.

## persistence-choice: Choose persistence to match what Redis stores
tags: redis, persistence, rdb, aof, durability, data loss, backups
keywords: data lost after restart
refs: https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/

A pure cache can run without persistence. If Redis holds data you need (sessions, queues, counters), enable AOF with `appendfsync everysec` (up to about a second of loss) plus RDB snapshots for backups, and test restores. Never treat Redis as the only copy of critical business data without that.

## connection-pooling-redis: Reuse pooled connections and set timeouts
tags: redis, connection pool, timeouts, client, reconnect, max clients
keywords: max number of clients reached
refs: https://redis.io/docs/latest/develop/clients/pools-and-muxing/

Create one client/pool per process and reuse it; opening a connection per request exhausts `maxclients` and adds latency. Configure connect and command timeouts and retry with backoff on reconnect, so a Redis outage degrades to cache misses rather than hung requests.

## pubsub-vs-streams: Use Streams, not Pub/Sub, when messages must not be lost
tags: redis, pub sub, streams, consumer groups, message queue, delivery guarantees
keywords: subscriber missed messages
refs: https://redis.io/docs/latest/develop/data-types/streams/

Pub/Sub is fire-and-forget: subscribers that are disconnected miss messages. For work queues and events that must be processed, use Streams with consumer groups (`XADD`, `XREADGROUP`, `XACK`), reclaim stuck messages with `XAUTOCLAIM`, and cap length with `MAXLEN ~`.
