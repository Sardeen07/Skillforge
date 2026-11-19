---
module: sqlite
capability: SQLite concurrency, durability and performance
technologies: sqlite
applies: sqlite, wal, embedded database, local database
checked_against: SQLite 3.46 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## wal-mode: Enable WAL mode for concurrent readers and a writer
tags: sqlite, wal, journal mode, concurrency, readers, writers, performance
keywords: database is locked
refs: https://www.sqlite.org/wal.html

In the default rollback-journal mode a writer blocks readers. `PRAGMA journal_mode=WAL;` (persistent per database) lets readers proceed during writes and usually speeds up writes. WAL requires all processes on the same host (not network file systems).

## busy-timeout: Set busy_timeout and keep write transactions short
tags: sqlite, busy timeout, database is locked, sqlite_busy, write lock, transactions
keywords: database is locked error
refs: https://www.sqlite.org/c3ref/busy_timeout.html

SQLite allows one writer at a time; without a busy timeout a second writer fails immediately with `SQLITE_BUSY`. Set `PRAGMA busy_timeout=5000`, keep write transactions short, and start transactions that will write with `BEGIN IMMEDIATE` so they take the write lock up front instead of failing on upgrade.

## batch-in-transactions-sqlite: Wrap bulk inserts in one transaction
tags: sqlite, bulk insert, transaction, performance, fsync, executemany
keywords: inserts very slow, 50 inserts per second
refs: https://www.sqlite.org/faq.html#q19

Each statement outside an explicit transaction is its own transaction with its own disk sync, limiting throughput to tens of inserts per second on some disks. Wrap bulk work in `BEGIN ... COMMIT` and use prepared statements (`executemany`); this commonly gives orders-of-magnitude speedups.

## foreign-keys-pragma: Turn on foreign key enforcement per connection
tags: sqlite, foreign keys, pragma, referential integrity, constraints, orphan rows
keywords: foreign key not enforced
refs: https://www.sqlite.org/foreignkeys.html#fk_enable

SQLite does not enforce foreign keys unless each connection runs `PRAGMA foreign_keys = ON;`. Set it in your connection setup (or driver option) and test that violations fail.

## strict-tables-types: Use STRICT tables or CHECK constraints for types
tags: sqlite, type affinity, strict tables, data types, check constraints, data quality
keywords: string stored in integer column
refs: https://www.sqlite.org/stricttables.html

SQLite's type affinity accepts a text value in an `INTEGER` column. Declare tables `STRICT` (3.37+) to enforce declared types, or add `CHECK (typeof(col) = 'integer')` constraints, so bad data fails at insert time.

## connection-per-thread-sqlite: Do not share one connection across threads without care
tags: sqlite, threads, connection, check_same_thread, python sqlite3, concurrency
keywords: ProgrammingError objects created in a thread
refs: https://docs.python.org/3/library/sqlite3.html#sqlite3.connect

Use one connection per thread (or a small pool), not one global connection shared by request threads. Python's `sqlite3` refuses cross-thread use by default (`check_same_thread`); disabling that without your own locking risks corrupted transaction state.

## sqlite-fit: Know when SQLite is the right database
tags: sqlite, architecture, embedded, scalability, write concurrency, client server database
keywords: should I use sqlite in production
refs: https://www.sqlite.org/whentouse.html

SQLite excels for embedded, single-host, read-heavy and moderate-write workloads (apps, edge caches, many websites). Prefer a client/server database when many hosts must write concurrently, when data lives on a network file system, or when you need high sustained write concurrency.

## sqlite-indexes-and-analyze: Index filtered columns and run PRAGMA optimize
tags: sqlite, index, query planner, analyze, optimize, explain query plan, performance
keywords: SCAN TABLE in explain query plan, slow sqlite query
refs: https://www.sqlite.org/queryplanner.html

Check plans with `EXPLAIN QUERY PLAN`: `SCAN table` on a large table means no usable index. Index columns used in `WHERE`, `JOIN` and `ORDER BY` (composite indexes in equality-then-range order), and run `PRAGMA optimize` before closing long-lived connections (or periodically) so the planner has statistics.

## sqlite-backups-online: Back up a live SQLite database with the backup API or VACUUM INTO
tags: sqlite, backup, vacuum into, wal, corruption, copy database file
keywords: copied the db file and it was corrupted
refs: https://www.sqlite.org/backup.html

Copying the database file while it is being written can produce a corrupt copy, and in WAL mode the `-wal` file holds recent commits. Use the online backup API (`sqlite3.Connection.backup` in Python) or `VACUUM INTO 'backup.db'`, and test restores.
