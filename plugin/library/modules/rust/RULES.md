---
module: rust
capability: Idiomatic Rust ownership, errors and async
technologies: rust
applies: rust, cargo, borrow, lifetime, tokio, serde
checked_against: The Rust Book, Rust API Guidelines, Tokio docs (Rust 1.8x)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## result-not-panic: Return Result for recoverable errors; reserve panic for bugs
tags: rust, result, error handling, panic, unwrap, expect, question mark
keywords: unwrap in production, thread panicked
refs: https://doc.rust-lang.org/book/ch09-03-to-panic-or-not-to-panic.html

Library and service code should propagate recoverable failures with `Result` and `?`, not `unwrap()`. Use `expect("invariant: ...")` only where failure means a bug, with a message stating the invariant. Use `thiserror` for library error enums and `anyhow` (with `.context(...)`) in applications.

## borrow-instead-of-clone: Borrow rather than clone to satisfy the borrow checker
tags: rust, borrow checker, clone, references, ownership, performance, lifetimes
keywords: clone everywhere, cannot borrow as mutable
refs: https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html

Sprinkling `.clone()` to silence borrow errors copies data and hides design problems. Accept `&str`/`&[T]`/`&T` in parameters, restructure so mutable borrows do not overlap (split structs, compute values before borrowing mutably), and use `Rc`/`Arc` only for genuinely shared ownership.

## accept-general-types: Accept &str, &[T] and impl Trait in function parameters
tags: rust, api design, string, slice, generics, impl trait, asref
keywords: &String parameter, &Vec parameter
refs: https://rust-lang.github.io/api-guidelines/flexibility.html

`fn f(s: &String)` and `fn g(v: &Vec<T>)` force callers to own those types; `&str` and `&[T]` accept more with no cost. Take `impl AsRef<Path>` or `impl Into<String>` where conversion is natural, and return concrete types.

## async-no-blocking: Do not block inside async tasks
tags: rust, async, tokio, blocking, spawn_blocking, std thread sleep, mutex
keywords: runtime stalls, executor blocked
refs: https://docs.rs/tokio/latest/tokio/task/fn.spawn_blocking.html

Blocking calls (`std::thread::sleep`, `std::fs`, synchronous DB clients, heavy CPU loops) inside an async task stall the worker thread and every task on it. Use async equivalents (`tokio::time::sleep`, `tokio::fs`) or move work to `tokio::task::spawn_blocking`. Do not hold a `std::sync::MutexGuard` across `.await`.

## shared-state-concurrency: Share state with Arc<Mutex<T>> or channels, scoped minimally
tags: rust, concurrency, arc, mutex, rwlock, channels, deadlock, send sync
keywords: lock held too long
refs: https://doc.rust-lang.org/book/ch16-03-shared-state.html

Wrap shared mutable state in `Arc<Mutex<T>>` (or `RwLock` for read-heavy data), keep the guard's scope as short as possible (copy out what you need, then drop), and prefer message passing (`mpsc`, `tokio::sync::mpsc`) for pipelines. For async code holding a lock across `.await`, use `tokio::sync::Mutex`.

## iterators-over-indexing: Use iterator adapters instead of index loops
tags: rust, iterator, map, filter, collect, bounds checks, performance
keywords: for i in 0..v.len()
refs: https://doc.rust-lang.org/book/ch13-02-iterators.html

Iterator chains (`iter().filter().map().collect()`) express intent, avoid off-by-one errors and typically eliminate bounds checks. Use `iter()`, `iter_mut()` or `into_iter()` deliberately, and `collect::<Result<Vec<_>, _>>()` to stop at the first error.

## unsafe-minimal: Keep unsafe blocks tiny and document their invariants
tags: rust, unsafe, soundness, ffi, raw pointers, miri, safety comment
keywords: unsafe everywhere
refs: https://doc.rust-lang.org/nomicon/working-with-unsafe.html

Wrap each `unsafe` operation in the smallest possible block inside a safe abstraction, and precede it with a `// SAFETY:` comment stating why the invariants hold. Test unsafe code under Miri (`cargo miri test`). Never expose a safe function that can cause undefined behavior for some inputs.

## clippy-and-fmt: Run cargo fmt, clippy and tests in CI
tags: rust, clippy, rustfmt, ci, lint, cargo, warnings
keywords: lint warnings ignored
refs: https://doc.rust-lang.org/clippy/

Run `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings` and `cargo test` in CI. Clippy catches common performance and correctness mistakes (needless clones, `len() == 0`, suspicious arithmetic). Commit `Cargo.lock` for binaries.

## string-types: Choose String, &str, Cow and PathBuf deliberately
tags: rust, string, str, cow, pathbuf, osstr, utf8, allocation
keywords: to_string everywhere, path as string
refs: https://doc.rust-lang.org/std/borrow/enum.Cow.html

Use `&str` for borrowed text, `String` when you own it, and `Cow<'_, str>` when a function usually returns its input unchanged. Use `Path`/`PathBuf` for file paths (they need not be UTF-8), and avoid `format!` allocations in hot loops (`write!` into a reused buffer).

## serde-validation: Deserialize into strict types with serde
tags: rust, serde, json, deserialization, validation, deny_unknown_fields, newtype
keywords: serde_json Value everywhere
refs: https://serde.rs/container-attrs.html#deny_unknown_fields

Deserialize input into concrete structs instead of `serde_json::Value`, use enums for closed sets, `#[serde(deny_unknown_fields)]` where typos must be rejected, and newtypes with validating `TryFrom` for constrained values (emails, IDs), so invalid states are unrepresentable after parsing.

## rust-error-context: Add context to errors at each boundary
tags: rust, error handling, anyhow, context, thiserror, error messages, debugging
keywords: error says only No such file or directory
refs: https://docs.rs/anyhow/latest/anyhow/trait.Context.html

A bare `?` on an `io::Error` reports "No such file or directory" with no hint of which file or why. Add `.with_context(|| format!("reading config {path:?}"))` (anyhow) or wrap in a `thiserror` variant carrying the operation and inputs, so the final error chain explains what failed.
