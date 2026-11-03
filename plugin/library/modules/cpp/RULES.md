---
module: cpp
capability: Modern C++ resource safety and correctness
technologies: cpp
applies: cpp, c++, raii, stl, templates, cmake
checked_against: C++ Core Guidelines and cppreference (C++20)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## raii-ownership: Manage every resource with RAII; no naked new/delete
tags: cpp, raii, unique_ptr, shared_ptr, memory leak, ownership, new delete
keywords: delete missing, exception leaks memory
refs: https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#Rr-raii

Own heap memory through `std::unique_ptr` (created with `std::make_unique`) and shared ownership through `std::shared_ptr` only when ownership is genuinely shared. Wrap files, sockets, locks and handles in classes whose destructor releases them. Raw pointers and references are for non-owning access only.

## rule-of-zero: Follow the rule of zero (or five)
tags: cpp, rule of five, rule of zero, copy constructor, move constructor, destructor, class design
keywords: double free, shallow copy
refs: https://en.cppreference.com/w/cpp/language/rule_of_three

Classes that hold only RAII members need no user-declared destructor, copy or move operations. If you write any of destructor/copy constructor/copy assignment/move constructor/move assignment, define or `= delete` all five, or the compiler-generated ones will double-free or leak.

## dangling-references: Never return or store references to temporaries or locals
tags: cpp, dangling reference, string_view, span, lifetime, undefined behavior, iterator invalidation
keywords: string_view to temporary, crash after push_back
refs: https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#Rf-dangle

`std::string_view`, `std::span`, references and iterators do not own data. Returning a `string_view` into a local `std::string`, or keeping a reference to a vector element across `push_back` (which may reallocate), is undefined behavior. Return owning types from functions and re-acquire iterators after mutation.

## const-correctness: Make everything const that can be
tags: cpp, const, constexpr, const reference, parameters, immutability
keywords: pass by value copies, accidental mutation
refs: https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#Rconst-immutable

Pass large read-only arguments as `const T&` (cheap types such as `int` or `string_view` by value), mark non-mutating member functions `const`, and use `constexpr` for compile-time constants. Const-correct interfaces document intent and let the compiler reject accidental writes.

## avoid-undefined-behavior: Treat undefined behavior as a bug and run sanitizers
tags: cpp, undefined behavior, sanitizer, asan, ubsan, signed overflow, out of bounds
keywords: works in debug crashes in release, -fsanitize
refs: https://clang.llvm.org/docs/AddressSanitizer.html

Signed overflow, out-of-bounds access, use-after-free, data races and uninitialized reads are UB; optimizers assume they never happen, so symptoms appear far away or only in release builds. Build tests with `-fsanitize=address,undefined` (and `thread` separately), compile with `-Wall -Wextra -Werror`, and use `.at()` or bounds checks at untrusted boundaries.

## move-semantics: Move instead of copying large objects, and do not use moved-from values
tags: cpp, move semantics, std move, rvalue, copy elision, performance
keywords: return std::move, unnecessary copy
refs: https://en.cppreference.com/w/cpp/utility/move

Pass sink arguments by value and `std::move` them into members; `std::move` large locals into containers. Do not write `return std::move(local);` (it disables copy elision). After a move, an object is valid but unspecified: only assign to it or destroy it.

## smart-container-choice: Default to std::vector and reserve capacity
tags: cpp, vector, list, map, unordered_map, reserve, cache locality, performance
keywords: std::list slow, many reallocations
refs: https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#Rsl-vector

`std::vector` is the right default: contiguous memory is cache-friendly and usually beats `std::list` even for middle insertions. Call `reserve(n)` when the size is known, prefer `unordered_map` for lookups when ordering is not needed, and use `emplace_back` for in-place construction.

## thread-safety-cpp: Protect shared data with mutexes or atomics, and lock with scoped guards
tags: cpp, thread, mutex, lock_guard, scoped_lock, atomic, data race, deadlock
keywords: lock unlock manually, deadlock two mutexes
refs: https://en.cppreference.com/w/cpp/thread/scoped_lock

Every piece of data written by one thread and read by another needs a mutex or `std::atomic`. Lock with `std::lock_guard`/`std::scoped_lock` (never manual `lock()`/`unlock()`), and lock multiple mutexes together with `std::scoped_lock(a, b)` to avoid deadlock. Use `std::jthread` so threads join on destruction.

## headers-and-build: Keep headers minimal and use include guards or pragma once
tags: cpp, header, include, compile time, forward declaration, cmake, odr
keywords: slow builds, multiple definition
refs: https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#S-source

Put declarations in headers and definitions in `.cpp` files (except templates and `inline`), protect headers with `#pragma once` or guards, include what you use, and forward-declare to cut compile times. Never put `using namespace` in a header. Define functions in headers only as `inline` or templates to avoid ODR violations.

## error-handling-cpp: Use exceptions or expected consistently, not error codes ignored
tags: cpp, exceptions, std expected, error codes, nodiscard, noexcept
keywords: ignored return value
refs: https://en.cppreference.com/w/cpp/utility/expected

Choose one error strategy per layer: exceptions for exceptional failures, or `std::expected<T, E>` (C++23) / a result type for expected failures. Mark functions whose results must be checked `[[nodiscard]]`, mark move constructors and destructors `noexcept`, and never let exceptions escape destructors.
