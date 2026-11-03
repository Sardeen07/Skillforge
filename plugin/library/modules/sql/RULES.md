---
module: sql
capability: Portable SQL query correctness and performance
technologies: sql
applies: sql, query, join, index, select, aggregate
checked_against: PostgreSQL 17, MySQL 8.4 and SQLite 3.46 documentation (portable behaviour)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## parameterized-queries: Always pass values as bound parameters
tags: sql, sql injection, parameterized query, prepared statement, placeholder, security
keywords: string concatenation, f-string query, user input in where clause
refs: https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html

Build SQL with placeholders (`?`, `$1`, `%s`, `:name`, per driver) and pass values separately; never concatenate or format user input into the SQL text. Placeholders cannot be used for identifiers or keywords: map dynamic column names and sort directions through an allowlist.

## null-semantics: Compare NULL with IS NULL and watch NOT IN with NULLs
tags: sql, null, three valued logic, not in, is null, coalesce, where clause
keywords: query returns no rows, = NULL
refs: https://www.postgresql.org/docs/current/functions-comparison.html

`col = NULL` is never true; use `IS NULL` / `IS DISTINCT FROM`. `x NOT IN (subquery)` returns no rows if the subquery yields any NULL; use `NOT EXISTS` instead. Aggregates such as `COUNT(col)` and `AVG` skip NULLs while `COUNT(*)` does not.

## sargable-predicates: Keep indexed columns bare in WHERE clauses
tags: sql, index, sargable, function on column, where clause, query optimization, full scan
keywords: lower(email) =, date(created_at) =, index not used
refs: https://use-the-index-luke.com/sql/where-clause/obfuscation

Wrapping an indexed column in a function or expression (`WHERE lower(email) = ?`, `WHERE date(created_at) = ?`, `WHERE amount + 1 > ?`) usually prevents index use. Rewrite as a range on the bare column (`created_at >= ? AND created_at < ?`) or create an expression index that matches the expression exactly.

## select-only-needed-columns: Select only the columns you need
tags: sql, select star, columns, covering index, network, performance, orm
keywords: select *, wide rows
refs: https://use-the-index-luke.com/sql/clustering/index-only-scan-covering-index

`SELECT *` transfers unused data, breaks when columns are added or reordered, and prevents index-only scans. List columns explicitly; for hot queries, an index containing all selected columns can answer without touching the table.

## joins-vs-subqueries: Use EXISTS for existence checks and avoid row-multiplying joins
tags: sql, join, exists, subquery, duplicate rows, distinct, aggregation
keywords: DISTINCT to fix duplicates, count too high
refs: https://www.postgresql.org/docs/current/functions-subquery.html#FUNCTIONS-SUBQUERY-EXISTS

Joining a one-to-many table to test existence multiplies rows, and `DISTINCT` then hides the bug at extra cost. Use `WHERE EXISTS (SELECT 1 FROM ... WHERE ...)`. When aggregating across two child tables, aggregate each in a subquery or CTE before joining, or sums double-count.

## keyset-pagination-sql: Paginate deep result sets with a keyset, not OFFSET
tags: sql, pagination, offset, keyset, cursor, order by, performance
keywords: page 1000 slow, limit offset
refs: https://use-the-index-luke.com/no-offset

`OFFSET n` reads and discards n rows, so late pages get slower and rows shift between requests. Remember the last row's sort key and continue from it: `WHERE (created_at, id) < (?, ?) ORDER BY created_at DESC, id DESC LIMIT 50`, with an index on `(created_at, id)`. Include a unique column to break ties.

## batch-writes: Batch inserts and updates inside one transaction
tags: sql, batch insert, bulk, transaction, multi row insert, performance, round trips
keywords: insert in a loop, one statement per row
refs: https://www.postgresql.org/docs/current/populate.html

Executing one statement and commit per row pays a round trip and a disk flush each time. Use multi-row `INSERT ... VALUES (...), (...)`, the driver's batch API (`executemany`, `COPY` in Postgres, `LOAD DATA` in MySQL), and wrap the batch in one transaction, in chunks of hundreds to a few thousand rows.

## explain-before-optimizing: Read the query plan before adding indexes
tags: sql, explain, query plan, explain analyze, index, optimization, slow query
keywords: guess an index, sequential scan
refs: https://www.postgresql.org/docs/current/using-explain.html

Run `EXPLAIN` (with `ANALYZE` on a safe copy, since it executes the query) to see whether a query scans, which index it uses and where estimated and actual row counts diverge. Optimize the step that dominates, then re-check. Find candidate queries from the slow-query log or `pg_stat_statements`, not intuition.

## composite-index-order: Order composite index columns by equality first, then range or sort
tags: sql, composite index, multi column index, column order, range, order by
keywords: index on (a, b) not used for b
refs: https://use-the-index-luke.com/sql/where-clause/the-equals-operator/concatenated-keys

A B-tree index on `(a, b)` serves filters on `a` or on `a` and `b`, but not on `b` alone. Put columns used with equality first, then the range or `ORDER BY` column: for `WHERE tenant_id = ? AND created_at > ? ORDER BY created_at`, index `(tenant_id, created_at)`.

## transactions-explicit: Group related writes in one transaction and keep it short
tags: sql, transaction, atomicity, commit, rollback, consistency, lock duration
keywords: partial update, half written order
refs: https://www.postgresql.org/docs/current/tutorial-transactions.html

Writes that must succeed or fail together (an order and its items, a debit and a credit) belong in one transaction with rollback on error. Keep transactions short: never wait for user input, network calls or slow computation while holding one, because its locks block other writers.

## count-efficiently: Avoid exact COUNT(*) on large tables for UI counters
tags: sql, count, performance, large table, estimate, pagination, total count
keywords: count(*) slow
refs: https://wiki.postgresql.org/wiki/Count_estimate

Exact `COUNT(*)` must visit every matching row (in Postgres and InnoDB). For "page 1 of N" UIs, show "next" without totals, use a cached or periodically refreshed counter, or use planner estimates; reserve exact counts for filtered queries backed by an index.

## upsert-atomic: Use the database's atomic upsert instead of select-then-insert
tags: sql, upsert, on conflict, insert or update, race condition, unique constraint, merge
keywords: duplicate key error under load
refs: https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT

`SELECT` then `INSERT` races under concurrency. Rely on a unique constraint and the native upsert: `INSERT ... ON CONFLICT (key) DO UPDATE` (Postgres, SQLite), `INSERT ... ON DUPLICATE KEY UPDATE` (MySQL), or `MERGE` where supported.
