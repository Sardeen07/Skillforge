---
module: swift
capability: Swift language safety and concurrency
technologies: swift
applies: swift, ios, optional, actor, async, xcode
checked_against: The Swift Programming Language (Swift 6) and Apple developer documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## avoid-force-unwrap: Unwrap optionals with guard let, not !
tags: swift, optional, force unwrap, guard let, if let, crash, nil
keywords: unexpectedly found nil, implicitly unwrapped optional
refs: https://docs.swift.org/swift-book/documentation/the-swift-programming-language/thebasics/#Optionals

`value!` crashes when the value is `nil`. Use `guard let value else { return / throw }` for early exit, `if let`, optional chaining with `??` defaults, and reserve `!` for invariants that are truly guaranteed (and say why in a comment). Avoid implicitly unwrapped optionals outside of IBOutlets.

## retain-cycles-closures: Capture self weakly in escaping closures that self retains
tags: swift, memory leak, retain cycle, weak self, closure, arc, unowned
keywords: deinit never called, view controller leak
refs: https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/#Strong-Reference-Cycles-for-Closures

When an object stores a closure (a completion handler property, a timer, a Combine sink in `cancellables`) that references `self`, ARC never frees either. Use `[weak self]` and `guard let self else { return }`. `unowned` is only for references that can never outlive `self`. Delegates should be `weak var`.

## structured-concurrency: Use async/await, TaskGroup and actors instead of completion handlers and locks
tags: swift, async await, concurrency, actor, task group, data race, sendable, swift 6
keywords: DispatchQueue, completion handler pyramid, data race
refs: https://docs.swift.org/swift-book/documentation/the-swift-programming-language/concurrency/

Write new asynchronous code with `async/await`, run independent work concurrently with `async let` or `withThrowingTaskGroup`, and protect mutable shared state with an `actor` instead of manual locks or serial queues. Enable Swift 6 strict concurrency checking so the compiler reports non-`Sendable` values crossing isolation domains.

## mainactor-ui: Update UI only on the main actor
tags: swift, mainactor, main thread, ui update, uikit, swiftui, concurrency
keywords: purple runtime warning, UI updated from background thread
refs: https://developer.apple.com/documentation/swift/mainactor

UIKit and SwiftUI state must be mutated on the main thread. Annotate view models and UI-facing types with `@MainActor`; when background work finishes, return to it with `await MainActor.run { ... }` or by calling a `@MainActor` method, rather than `DispatchQueue.main.async` scattered through the code.

## task-cancellation: Check for cancellation in long-running tasks
tags: swift, task, cancellation, async, checkCancellation, structured concurrency
keywords: task keeps running after view disappears
refs: https://developer.apple.com/documentation/swift/task/checkcancellation()

Cancellation in Swift is cooperative: a cancelled `Task` keeps running until it checks. Call `try Task.checkCancellation()` or test `Task.isCancelled` inside loops, and keep the `Task` handle to cancel it (SwiftUI's `.task {}` modifier cancels automatically when the view disappears).

## value-types-default: Prefer structs and enums; use classes for identity
tags: swift, struct, class, value type, reference type, enum, immutability
keywords: shared mutable state, copy on write
refs: https://developer.apple.com/documentation/swift/choosing-between-structures-and-classes

Model data with structs and enums (value semantics, thread-friendly, no retain cycles). Use classes only when identity or shared mutable state is the point, or for Objective-C interop. Make stored properties `let` unless they must change.

## error-handling-swift: Throw typed errors and do not hide them with try?
tags: swift, error handling, throws, try, do catch, result, try optional
keywords: try? swallowed error, silent failure
refs: https://docs.swift.org/swift-book/documentation/the-swift-programming-language/errorhandling/

Define errors as enums conforming to `Error` (or `LocalizedError` for user-facing messages), propagate with `throws`, and handle with `do/catch`. `try?` discards the error: use it only when failure genuinely means "no value", and avoid `try!` outside tests.

## codable-models: Use Codable with explicit keys and decoding strategies
tags: swift, codable, json, decoding, encoding, api, date decoding
keywords: keyNotFound, snake_case keys
refs: https://developer.apple.com/documentation/foundation/archives_and_serialization/encoding_and_decoding_custom_types

Decode API payloads into `Codable` structs. Configure `JSONDecoder.keyDecodingStrategy = .convertFromSnakeCase` and an explicit `dateDecodingStrategy` (e.g. `.iso8601`), make fields optional only when the API truly omits them, and surface `DecodingError` details in logs instead of failing silently.
