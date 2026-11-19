---
module: concurrency
capability: Concurrency correctness across languages
technologies:
applies: concurrency, threads, race condition, deadlock, locks, async, parallelism
checked_against: Java Concurrency in Practice principles, Go memory model, Rust Book chapter 16
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## check-then-act-races: Make check-then-act sequences atomic
tags: concurrency, race condition, check then act, atomicity, compare and swap, locks
keywords: two requests both passed the check
refs: https://docs.oracle.com/javase/tutorial/essential/concurrency/sync.html

`if not exists: create`, `if balance >= x: withdraw` and lazy initialization race when two threads or requests interleave. Perform the check and the action atomically: under one lock, with an atomic primitive (compare-and-swap, `putIfAbsent`), or in the database with a constraint or conditional update.

## lock-ordering-deadlock: Acquire multiple locks in one global order, and hold locks briefly
tags: concurrency, deadlock, lock ordering, mutex, timeouts, lock contention
keywords: application hangs, threads waiting forever
refs: https://wiki.sei.cmu.edu/confluence/display/java/LCK07-J.+Avoid+deadlock+by+requesting+and+releasing+locks+in+the+same+order

Deadlocks arise when threads take the same locks in different orders. Define an order (by ID or address) and always acquire in it, never call unknown code or do I/O while holding a lock, keep critical sections short, and use lock timeouts (`tryLock`) where you can recover.

## immutable-shared-data: Share immutable data; confine mutable state
tags: concurrency, immutability, thread confinement, shared state, message passing, actors
keywords: who modified this object
refs: https://doc.rust-lang.org/book/ch16-00-concurrency.html

The safest shared data is immutable. Confine mutable state to a single thread, task or actor and communicate with messages or channels; when sharing is unavoidable, encapsulate state and its lock together so no caller can access it unsynchronized.

## bounded-concurrency: Bound concurrency with pools and semaphores
tags: concurrency, thread pool, semaphore, backpressure, resource exhaustion, parallelism limit
keywords: spawned 10000 threads, too many open connections
refs: https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore

Unbounded parallelism (a thread or task per item) exhausts memory, file descriptors, connection pools and downstream rate limits. Use fixed-size worker pools or semaphores sized to the bottleneck resource, and bounded queues between producers and consumers.

## visibility-memory-model: Synchronize to make writes visible across threads
tags: concurrency, memory model, visibility, volatile, atomics, happens before, data race
keywords: flag change never seen by other thread
refs: https://go.dev/ref/mem

Without synchronization a write in one thread may never become visible to another, or become visible out of order. Publish shared data through locks, atomics, channels or thread-safe queues; a plain boolean "stop" flag needs to be atomic/volatile. Run race detectors (Go `-race`, ThreadSanitizer) in tests.

## cancellation-and-timeouts-concurrency: Propagate cancellation and time limits to concurrent work
tags: concurrency, cancellation, timeouts, structured concurrency, orphan tasks, futures
keywords: work continues after client disconnected
refs: https://docs.python.org/3/library/asyncio-task.html#task-groups

When a request is cancelled or times out, its child tasks should stop too. Use structured concurrency (task groups, `errgroup`, `coroutineScope`) so children are cancelled with their parent and errors propagate, and pass deadlines down instead of letting orphaned work run.

## idempotent-retries-concurrency: Design for concurrent duplicates in distributed workers
tags: concurrency, workers, duplicate processing, idempotency, distributed locks, queue consumers
keywords: two workers processed the same job
refs: https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE

Multiple workers can pick up the same item after timeouts or redeliveries. Claim work atomically (`UPDATE ... WHERE status='pending' ... RETURNING`, `SELECT ... FOR UPDATE SKIP LOCKED`), make processing idempotent, and record completion in the same transaction as the side effect.

## async-vs-threads-choice: Pick the concurrency model by workload
tags: concurrency, async, threads, processes, io bound, cpu bound, event loop
keywords: async made it slower
refs: https://docs.python.org/3/library/concurrent.futures.html

Async/await and event loops suit many concurrent I/O waits with low overhead; threads suit blocking libraries; processes or native parallelism suit CPU-bound work in runtimes with a global lock. Mixing models (blocking calls on an event loop) is the most common performance bug.

## multi-process-coordination: Coordinate across worker processes in shared state, not in-process locks
tags: concurrency, multiprocessing, gunicorn workers, uwsgi, in process lock, race condition, database lock
keywords: threading lock did not help, works in dev fails with several workers, flash sale oversold
refs: https://gunicorn.org/design/

Production web servers run several worker processes (gunicorn, uWSGI, Puma, PM2 cluster, multiple containers), and a `threading.Lock` or in-memory flag only coordinates threads inside one process. Enforce invariants where all workers meet: an atomic conditional `UPDATE ... WHERE stock >= ?`, a unique constraint, a row lock in a transaction, or a distributed lock with fencing.
