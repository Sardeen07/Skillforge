---
module: database-design
capability: Schema design, indexing strategy, transactions and migrations
technologies:
applies: database, schema, index, migration, transaction, normalization, concurrency
checked_against: PostgreSQL 17 documentation, Use The Index Luke, Designing Data-Intensive Applications
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## constraints-enforce-invariants: Enforce invariants with constraints, not only application code
tags: database design, constraints, unique, foreign key, not null, check, data integrity
keywords: duplicate rows despite validation, orphan records
refs: https://www.postgresql.org/docs/current/ddl-constraints.html

Application checks race and are bypassed by scripts and other services. Declare `NOT NULL`, `UNIQUE`, `FOREIGN KEY` and `CHECK` constraints for every invariant the data must satisfy, and translate constraint violations into domain errors in code.

## normalize-then-denormalize: Normalize first; denormalize deliberately with a sync plan
tags: database design, normalization, denormalization, schema design, redundancy, consistency
keywords: same data stored in three tables
refs: https://www.postgresql.org/docs/current/ddl.html

Start with a normalized schema (each fact stored once). Denormalize only for a measured read bottleneck, and decide how the copy stays correct (trigger, materialized view with refresh schedule, or event-driven update). Unmaintained copies become silent inconsistencies.

## index-for-queries: Index for actual query patterns and remove unused indexes
tags: database design, indexing, index strategy, write amplification, unused indexes, foreign keys
keywords: index every column
refs: https://use-the-index-luke.com/

Every index speeds some reads and slows every write. Derive indexes from the queries that run most and slowest (filter, join and sort columns), index foreign-key columns used in joins and cascading deletes, and periodically drop indexes the statistics show are never used.

## money-and-time-types: Use exact numeric types for money and timezone-aware timestamps
tags: database design, data types, decimal, numeric, money, timestamp, timezone, utc
keywords: float rounding errors, wrong time after DST
refs: https://www.postgresql.org/docs/current/datatype-datetime.html

Store currency in `NUMERIC/DECIMAL` (or integer minor units) with the currency code, never `FLOAT`. Store instants as timezone-aware timestamps in UTC (`timestamptz` in Postgres) and convert at the edges; store the user's IANA time zone separately when local-time rules matter.

## expand-contract-migrations: Change schemas with expand-and-contract migrations
tags: database design, migrations, zero downtime, expand contract, rolling deploy, backfill, rename column
keywords: renamed column broke running app
refs: https://martinfowler.com/bliki/ParallelChange.html

During a rolling deploy old and new code run together. Expand first (add the new column/table, write to both), backfill in batches, switch reads, then contract (drop the old column) in a later release. Never rename or drop a column in the same release that stops using it.

## transaction-isolation-anomalies: Pick isolation levels knowingly and retry serialization failures
tags: database design, transactions, isolation level, serializable, lost update, write skew, concurrency
keywords: lost update, double booking
refs: https://www.postgresql.org/docs/current/transaction-iso.html

READ COMMITTED (the common default) permits lost updates and write skew in read-then-write logic. Use atomic updates (`UPDATE ... SET stock = stock - 1 WHERE stock > 0`), explicit row locks (`SELECT ... FOR UPDATE`), or SERIALIZABLE isolation with automatic retry of serialization failures.

## optimistic-locking: Use a version column for optimistic concurrency on edits
tags: database design, optimistic locking, version column, concurrency, lost update, conflict
keywords: two users overwrote each other
refs: https://martinfowler.com/eaaCatalog/optimisticOfflineLock.html

For user edits that span requests, store a `version` (or `updated_at`) and update with `WHERE id = ? AND version = ?`, incrementing it; zero rows affected means someone else changed the record, so report a conflict (HTTP 409) instead of silently overwriting.

## soft-delete-tradeoffs: Use soft deletes only with indexes and unique constraints that account for them
tags: database design, soft delete, deleted_at, unique constraint, partial index, data retention
keywords: deleted rows still unique, every query forgets the filter
refs: https://www.postgresql.org/docs/current/indexes-partial.html

`deleted_at` columns must be filtered in every query and break plain unique constraints. If you need them, enforce uniqueness with a partial unique index (`WHERE deleted_at IS NULL`), centralize the filter (views or default scopes), and still honor hard-deletion requirements such as privacy erasure.

## connection-pool-sizing: Size connection pools to the database, not to the app
tags: database design, connection pooling, pool size, pgbouncer, max connections, serverless
keywords: too many connections, connection storms
refs: https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing

A database performs best with a limited number of active connections (on the order of a few per CPU core). Sum pool sizes across all app instances and keep the total below the database limit, put a pooler (PgBouncer, RDS Proxy) in front of serverless or many-instance deployments, and let requests queue for a connection rather than opening more.

## partition-and-archive: Archive or partition data that grows without bound
tags: database design, partitioning, archiving, retention, large tables, time series
keywords: table with billions of rows, vacuum slow
refs: https://www.postgresql.org/docs/current/ddl-partitioning.html

Event, log and history tables grow forever. Define a retention policy, partition by time so old data is dropped by detaching partitions (cheap) rather than mass `DELETE` (slow, bloating), and move cold data to cheaper storage.
