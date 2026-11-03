---
module: java
capability: Java correctness, concurrency and resource handling
technologies: java
applies: java, jvm, maven, gradle, junit
checked_against: Java SE 21 API documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## equals-hashcode-contract: Override equals and hashCode together, or use records
tags: java, equals, hashcode, hashmap, hashset, record, value object
keywords: duplicate in set, map lookup fails
refs: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html#hashCode()

Objects that are `equals` must have equal hash codes, or `HashMap`/`HashSet` lookups miss them. Override both from the same fields (or neither). For immutable data carriers use a `record`, which generates consistent `equals`, `hashCode` and `toString`. Never use mutable fields in `hashCode` of objects stored in hash collections.

## try-with-resources: Close streams, connections and statements with try-with-resources
tags: java, try with resources, autocloseable, resource leak, jdbc, stream, connection pool
keywords: finally close, connection leak, too many open files
refs: https://docs.oracle.com/javase/tutorial/essential/exceptions/tryResourceClose.html

Declare every `AutoCloseable` (JDBC `Connection`/`PreparedStatement`/`ResultSet`, streams, `HttpClient` responses) in a `try (...)` header so it closes in reverse order on every path, with suppressed exceptions preserved. Leaked JDBC connections exhaust the pool and hang the service.

## optional-usage: Use Optional only as a return type, never as a field or parameter
tags: java, optional, null, return type, nullpointerexception
keywords: Optional.get, isPresent then get
refs: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html

`Optional` signals "may be absent" from a method result. Consume it with `map`, `orElse`, `orElseThrow` or `ifPresent`, not `isPresent()` + `get()`. Do not use it for fields, parameters or collections (return an empty collection instead), and never return `null` from a method declared to return `Optional`.

## concurrent-collections: Use java.util.concurrent types, not synchronized wrappers or HashMap, across threads
tags: java, concurrency, concurrenthashmap, thread safety, race condition, atomic, collections
keywords: HashMap infinite loop, ConcurrentModificationException, check then act
refs: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html

A `HashMap` shared between threads can corrupt itself. Use `ConcurrentHashMap` and its atomic operations (`computeIfAbsent`, `merge`) instead of check-then-act sequences (`if (!map.containsKey(k)) map.put(k, v)` races). Use `AtomicLong`/`LongAdder` for counters and `CopyOnWriteArrayList` for rarely-written listener lists.

## executor-lifecycle: Use executors (or virtual threads) and shut them down
tags: java, executorservice, threads, virtual threads, thread pool, shutdown, concurrency
keywords: new Thread, JVM does not exit, thread leak
refs: https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html

Do not spawn raw `Thread`s per task. For blocking I/O-heavy work on Java 21+, `Executors.newVirtualThreadPerTaskExecutor()` scales to many concurrent tasks; for CPU-bound work use a fixed pool sized to cores. Use try-with-resources on the `ExecutorService` (Java 19+) or call `shutdown()` and `awaitTermination()`. Avoid `synchronized` blocks around blocking I/O in virtual threads before Java 24, since they pin the carrier thread.

## string-building: Use StringBuilder in loops and String.join for lists
tags: java, string, stringbuilder, concatenation, performance, loop
keywords: += in loop
refs: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/StringBuilder.html

`s += x` in a loop creates a new string each iteration (quadratic copying). Use a `StringBuilder`, or `String.join`/`Collectors.joining` for collections. Single-expression concatenation outside loops is fine; the compiler optimizes it.

## immutability-defaults: Prefer immutable objects and defensive copies
tags: java, immutable, final, record, list of, defensive copy, thread safety
keywords: caller modified my list
refs: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html#unmodifiable

Make fields `final`, use records, and return `List.copyOf(...)`/`List.of(...)` rather than exposing internal mutable collections. Immutable objects are thread-safe without locking and cannot be changed by callers. Note `List.of` rejects `null` elements.

## checked-exceptions-boundaries: Do not swallow exceptions; wrap with cause
tags: java, exception, checked exception, error handling, catch, logging, cause
keywords: catch Exception e printStackTrace, empty catch
refs: https://docs.oracle.com/javase/tutorial/essential/exceptions/chained.html

Empty `catch` blocks and `e.printStackTrace()` lose errors. Catch what you can handle; otherwise wrap in a domain or unchecked exception with the original as the cause (`throw new StorageException("write failed", e)`). Restore the interrupt flag when catching `InterruptedException`: `Thread.currentThread().interrupt();`.

## streams-judiciously: Use streams for transformations, not for side effects or hot loops
tags: java, streams, lambda, collectors, parallel stream, performance, side effects
keywords: forEach add to list, parallelStream slower
refs: https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/package-summary.html

Streams should be side-effect-free pipelines ending in a collector. Do not mutate external state from `forEach`/`map`. `parallelStream()` uses the shared common ForkJoinPool; use it only for large, CPU-bound, independent work you have measured, never for blocking I/O.

## junit5-assertions: Write JUnit 5 tests with clear assertions and parameterization
tags: java, junit, testing, assertj, parameterized test, mockito
keywords: assertTrue(a.equals(b)), many similar tests
refs: https://junit.org/junit5/docs/current/user-guide/#writing-tests-parameterized-tests

Use `assertEquals(expected, actual)` or AssertJ (`assertThat(x).isEqualTo(y)`) rather than `assertTrue(a.equals(b))`, which hides the values on failure. Express input tables with `@ParameterizedTest` + `@CsvSource`/`@MethodSource`, use `assertThrows` for exceptions, and mock only collaborators you own the contract of.
