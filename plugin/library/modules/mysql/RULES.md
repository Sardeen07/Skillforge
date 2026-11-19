---
module: mysql
capability: MySQL/InnoDB schema, indexing and locking
technologies: mysql
applies: mysql, mariadb, innodb, index, transaction, replication
checked_against: MySQL 8.4 Reference Manual
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## utf8mb4-charset: Use utf8mb4, never utf8 (utf8mb3)
tags: mysql, charset, utf8mb4, unicode, emoji, collation, encoding
keywords: incorrect string value, emoji breaks insert
refs: https://dev.mysql.com/doc/refman/8.4/en/charset-unicode-utf8mb4.html

MySQL's legacy `utf8` is a 3-byte encoding that cannot store emoji or other 4-byte characters. Use `utf8mb4` with a modern collation (`utf8mb4_0900_ai_ci`, the 8.0+ default) for databases, tables and connections (`charset=utf8mb4` in the driver DSN).

## innodb-primary-key: Give every InnoDB table a compact, monotonic primary key
tags: mysql, innodb, primary key, clustered index, uuid, auto increment, insert performance
keywords: random uuid primary key slow inserts
refs: https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html

InnoDB stores rows in primary-key order and every secondary index contains the primary key. Random UUIDv4 keys cause page splits and bloat every index; use `BIGINT AUTO_INCREMENT` or time-ordered IDs (UUIDv7, or `UUID_TO_BIN(uuid, 1)` stored as `BINARY(16)`).

## covering-and-prefix-indexes: Design composite and covering indexes from real queries
tags: mysql, index, composite index, covering index, explain, leftmost prefix, query optimization
keywords: using filesort, using temporary
refs: https://dev.mysql.com/doc/refman/8.4/en/multiple-column-indexes.html

InnoDB uses the leftmost prefix of a composite index. Check `EXPLAIN` (or `EXPLAIN ANALYZE`) for `Using filesort` and `Using temporary`, and build indexes that match `WHERE` equality columns, then the range/`ORDER BY` column; adding selected columns makes the index covering (`Using index`).

## gap-locks-isolation: Understand REPEATABLE READ gap locks and deadlocks
tags: mysql, innodb, isolation level, gap locks, next key locks, deadlock, repeatable read
keywords: deadlock found when trying to get lock, insert blocked
refs: https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html#innodb-gap-locks

InnoDB's default REPEATABLE READ takes next-key (gap) locks on ranges scanned by locking reads and updates, so unindexed `UPDATE ... WHERE` can lock large ranges and cause deadlocks. Index the columns used in locking statements, keep transactions short, access rows in a consistent order, and retry transactions that fail with deadlock error 1213.

## online-schema-changes: Use online DDL or a migration tool for large tables
tags: mysql, schema migration, online ddl, alter table, gh-ost, pt-online-schema-change, downtime
keywords: alter table locked production
refs: https://dev.mysql.com/doc/refman/8.4/en/innodb-online-ddl-operations.html

Many `ALTER TABLE` operations rebuild the table. Specify `ALGORITHM=INSTANT` or `ALGORITHM=INPLACE, LOCK=NONE` so MySQL fails instead of silently locking, and for operations that require a copy on large tables use gh-ost or pt-online-schema-change. Watch replication lag during migrations.

## strict-sql-mode: Keep strict SQL mode on
tags: mysql, sql mode, strict mode, data truncation, validation, only_full_group_by
keywords: data silently truncated, zero dates
refs: https://dev.mysql.com/doc/refman/8.4/en/sql-mode.html#sql-mode-strict

Without `STRICT_TRANS_TABLES`, MySQL silently truncates strings, clamps numbers and inserts zero dates. Keep the 8.x default modes (strict, `ONLY_FULL_GROUP_BY`, `NO_ZERO_DATE`) and fix queries that break rather than relaxing the mode.

## replica-lag-reads: Account for replication lag when reading from replicas
tags: mysql, replication, read replica, replication lag, consistency, read your writes
keywords: just saved data missing
refs: https://dev.mysql.com/doc/refman/8.4/en/replication.html

Asynchronous replicas lag behind the source, sometimes by seconds. Route reads that must reflect a user's recent write to the source (or wait for the replica to catch up using GTIDs), and monitor lag; use replicas for analytics and tolerant reads.

## mysql-connection-handling: Handle wait_timeout and pool connections correctly
tags: mysql, connection pool, wait timeout, server has gone away, pool recycle, lost connection
keywords: MySQL server has gone away, Lost connection to MySQL server during query
refs: https://dev.mysql.com/doc/refman/8.4/en/gone-away.html

MySQL closes idle connections after `wait_timeout` (8 hours by default, often lower on managed services), so pooled connections die silently. Configure the pool to recycle connections before that (`pool_recycle` in SQLAlchemy) and to validate on checkout (`pool_pre_ping`), and keep the pool size within `max_connections` across all instances.

## mysql-json-columns: Index JSON fields through generated columns
tags: mysql, json, generated columns, functional index, multi valued index, query performance
keywords: JSON_EXTRACT in where clause slow
refs: https://dev.mysql.com/doc/refman/8.4/en/create-table-secondary-indexes.html

A `WHERE JSON_EXTRACT(doc, '$.status') = ?` filter cannot use a normal index. Add a stored or virtual generated column for the path and index it, use a functional index on the expression (8.0.13+), or a multi-valued index for JSON arrays, and query through the same expression.
