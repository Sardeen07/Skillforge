---
module: kotlin
capability: Kotlin null safety and coroutines
technologies: kotlin
applies: kotlin, coroutine, flow, suspend, null safety
checked_against: Kotlin documentation (Kotlin 2.x, kotlinx.coroutines 1.8)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## null-safety: Avoid !! and model absence with nullable types
tags: kotlin, null safety, nullable, double bang, elvis, let, npe
keywords: KotlinNullPointerException, !!
refs: https://kotlinlang.org/docs/null-safety.html

`!!` turns a compile-time guarantee back into a runtime crash. Use safe calls (`user?.name`), the Elvis operator for defaults or early returns (`val id = req.id ?: return badRequest()`), and `requireNotNull(x) { "why" }` for invariants. Values from Java APIs are platform types: declare them nullable at the boundary.

## structured-concurrency-scopes: Launch coroutines in a lifecycle scope, never GlobalScope
tags: kotlin, coroutines, globalscope, coroutinescope, viewmodelscope, structured concurrency, leak
keywords: coroutine keeps running, leaked job
refs: https://kotlinlang.org/docs/coroutines-basics.html#structured-concurrency

`GlobalScope.launch` creates work nobody cancels. Launch in a scope tied to a lifecycle (`viewModelScope`, `lifecycleScope`, a service-owned `CoroutineScope(SupervisorJob() + dispatcher)` that you cancel on shutdown), and use `coroutineScope { }` inside suspend functions so children finish or fail together.

## dispatchers-for-blocking: Run blocking calls on Dispatchers.IO
tags: kotlin, coroutines, dispatchers, blocking io, withcontext, main thread, anr
keywords: network on main thread, UI freezes
refs: https://kotlinlang.org/docs/coroutine-context-and-dispatchers.html

Suspend functions must be main-safe: wrap blocking I/O in `withContext(Dispatchers.IO) { ... }` and CPU-heavy work in `Dispatchers.Default`. Inject dispatchers rather than hardcoding them, so tests can substitute a test dispatcher.

## cancellation-cooperation: Do not swallow CancellationException
tags: kotlin, coroutines, cancellation, cancellationexception, runcatching, try catch
keywords: coroutine does not cancel, catch Exception
refs: https://kotlinlang.org/docs/cancellation-and-timeouts.html

Cancellation is delivered as `CancellationException`. A `catch (e: Exception)` or `runCatching` around suspend calls catches it and keeps the coroutine alive. Rethrow it (`catch (e: CancellationException) { throw e }`) or catch narrower exceptions, and call `ensureActive()` in long CPU loops.

## flow-collection: Collect flows lifecycle-aware and expose StateFlow from view models
tags: kotlin, flow, stateflow, sharedflow, collect, lifecycle, repeatOnLifecycle
keywords: collecting in background, flow restarts
refs: https://developer.android.com/kotlin/flow/stateflow-and-sharedflow

Expose UI state as `StateFlow` (via `stateIn(scope, SharingStarted.WhileSubscribed(5_000), initial)`), use `SharedFlow` for one-off events, and collect in Android UI with `repeatOnLifecycle(Lifecycle.State.STARTED)` or `collectAsStateWithLifecycle()` so collection stops in the background.

## data-classes-immutability: Use data classes with val and copy for state
tags: kotlin, data class, immutability, val, copy, value object, sealed class
keywords: var properties, mutable state shared
refs: https://kotlinlang.org/docs/data-classes.html

Model state with `data class` of `val` properties and update with `copy(...)`; expose read-only `List`/`Map` types. Model closed sets of states or results with `sealed interface`, so `when` is exhaustive and the compiler flags unhandled cases.

## scope-functions-sparingly: Use scope functions for clarity, not nesting
tags: kotlin, scope functions, let, apply, also, run, readability
keywords: nested let chains
refs: https://kotlinlang.org/docs/scope-functions.html

`apply` configures an object, `also` adds side effects, `let` maps nullable values, `run`/`with` group calls. Nesting several of them makes `it`/`this` ambiguous; name the lambda parameter or use plain local variables when it stops being obvious.

## java-interop-annotations: Annotate Kotlin APIs used from Java
tags: kotlin, java interop, jvmstatic, jvmoverloads, nullability annotations, jvm
keywords: called from java, default arguments in java
refs: https://kotlinlang.org/docs/java-to-kotlin-interop.html

Java callers do not see Kotlin default arguments or companion objects ergonomically. Add `@JvmOverloads` for default parameters, `@JvmStatic` for companion functions and `@Throws` for checked exceptions Java must catch, and annotate Java APIs with `@Nullable`/`@NonNull` so Kotlin sees precise types.
