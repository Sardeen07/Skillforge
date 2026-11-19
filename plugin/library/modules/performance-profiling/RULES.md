---
module: performance-profiling
capability: Performance profiling, algorithmic complexity and memory management
technologies:
applies: profiling, memory leak, cpu, latency, complexity, optimization, benchmark
checked_against: Brendan Gregg's methodology (USE method), language profiler documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## profile-before-optimizing: Profile to find the bottleneck before optimizing
tags: performance, profiling, bottleneck, flame graph, cpu profile, measurement, premature optimization
keywords: guessed optimization did nothing
refs: https://www.brendangregg.com/flamegraphs.html

Measure first: reproduce the slow case, profile it (py-spy, cProfile, async-profiler, pprof, Chrome DevTools, perf) and read a flame graph to find where time actually goes. Optimize the dominant cost, then measure again with the same workload to confirm the gain.

## algorithmic-complexity: Fix quadratic algorithms before micro-optimizing
tags: performance, algorithmic complexity, big o, nested loops, quadratic, data structures, hash map
keywords: fine with 100 items, unusable with 100000
refs: https://en.wikipedia.org/wiki/Time_complexity

Nested loops over two collections, repeated linear searches and repeated sorting are O(n²) or worse and dominate at scale. Index one side in a hash map or set, sort once and use binary search or a merge, or push the work into a database query with an index. A better algorithm beats any constant-factor tweak.

## benchmark-properly: Benchmark with warmup, repetitions and realistic data
tags: performance, benchmarking, microbenchmark, warmup, variance, statistics, jit
keywords: benchmark numbers inconsistent
refs: https://github.com/openjdk/jmh

Use a benchmarking harness (JMH, pytest-benchmark, Go `testing.B`, hyperfine) that warms up, repeats and reports variance; run on quiet machines with production-like data sizes; and compare distributions rather than single runs. Microbenchmarks can be optimized away entirely by compilers if results are unused.

## memory-leaks-find: Find memory leaks by comparing heap snapshots
tags: memory management, memory leak, heap snapshot, garbage collection, caches, listeners, profiling
keywords: memory grows until oom
refs: https://developer.chrome.com/docs/devtools/memory-problems

Take heap snapshots before and after repeating an operation and look for objects whose count grows (tracemalloc, Chrome/Node heap snapshots, `jmap`/Eclipse MAT, pprof heap). Typical culprits: unbounded caches and maps, listeners and timers never removed, closures capturing large objects, and global registries.

## bounded-caches: Bound in-process caches by size and age
tags: memory management, caching, lru cache, memoization, memory growth, eviction
keywords: memoize everything, cache grows forever
refs: https://docs.python.org/3/library/functools.html#functools.lru_cache

An unbounded dictionary used as a cache is a memory leak. Use an LRU/LFU cache with a maximum size and TTL (`functools.lru_cache(maxsize=...)`, Caffeine, `lru-cache`), key it carefully (per-tenant data must not be shared), and measure the hit rate to confirm it helps.

## reduce-allocations-hot-paths: Reduce allocations and copies in hot paths
tags: performance, allocations, garbage collection, object pooling, copying, buffers, gc pauses
keywords: gc pauses, high allocation rate
refs: https://go.dev/doc/gc-guide

On hot paths, reuse buffers, preallocate collections to known sizes, stream instead of materializing whole datasets, and avoid repeated string formatting or boxing. Confirm with an allocation profile; for most code, readable allocations are fine.

## use-method-resources: Diagnose system slowness with utilization, saturation and errors
tags: performance, use method, cpu, memory, disk io, network, saturation, capacity
keywords: server slow but cpu low
refs: https://www.brendangregg.com/usemethod.html

For each resource (CPU, memory, disk, network, connection pools, thread pools) check utilization, saturation (queueing) and errors. Low CPU with high latency usually means waiting: on locks, I/O, a pool, or a downstream dependency.

## load-test-before-launch: Load-test critical paths with realistic traffic shapes
tags: performance, load testing, k6, locust, capacity, latency percentiles, launch
keywords: site fell over on launch day
refs: https://k6.io/docs/

Before a launch or a big change, load-test the critical user paths with production-like data volumes and traffic mix (k6, Locust, Gatling), ramp past the expected peak, and watch p95/p99 latency, error rate and saturation of downstream dependencies (database connections, queues) to find the first bottleneck.
