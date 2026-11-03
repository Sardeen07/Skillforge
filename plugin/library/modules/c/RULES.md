---
module: c
capability: C memory safety and secure coding
technologies: c
applies: c, malloc, pointer, buffer, string
checked_against: SEI CERT C Coding Standard and cppreference (C17)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## bounded-string-functions: Never use gets, strcpy or sprintf on unbounded input
tags: c, buffer overflow, strcpy, strncpy, snprintf, gets, string, security
keywords: stack smashing, overflow
refs: https://wiki.sei.cmu.edu/confluence/display/c/STR31-C.+Guarantee+that+storage+for+strings+has+sufficient+space+for+character+data+and+the+null+terminator

`gets` was removed in C11; `strcpy`, `strcat` and `sprintf` write past the buffer when the source is longer than expected. Use `snprintf(buf, sizeof buf, ...)` and check its return value for truncation, track lengths explicitly, and remember `strncpy` does not null-terminate when the source fills the buffer.

## check-allocations: Check every allocation and size calculation
tags: c, malloc, calloc, realloc, null, integer overflow, memory
keywords: realloc leak, size overflow, malloc returns NULL
refs: https://wiki.sei.cmu.edu/confluence/display/c/MEM04-C.+Beware+of+zero-length+allocations

Check `malloc`/`calloc`/`realloc` for `NULL`. Assign `realloc` to a temporary, or the original block leaks on failure. Guard size arithmetic against overflow before allocating (`if (n > SIZE_MAX / sizeof *p) fail;`), or use `calloc(n, size)`, which checks the multiplication.

## free-once-and-null: Free each allocation exactly once and set the pointer to NULL
tags: c, free, double free, use after free, dangling pointer, memory leak, ownership
keywords: crash in free, heap corruption
refs: https://wiki.sei.cmu.edu/confluence/display/c/MEM30-C.+Do+not+access+freed+memory

Document which function owns each allocation. After `free(p)`, set `p = NULL` so a second free is harmless and a later use crashes deterministically. Use a single cleanup path (`goto cleanup;`) in functions with several allocations, and run tests under AddressSanitizer or Valgrind.

## integer-overflow-c: Prevent signed overflow and check conversions
tags: c, integer overflow, signed, unsigned, size_t, conversion, undefined behavior
keywords: negative length, wraparound
refs: https://wiki.sei.cmu.edu/confluence/display/c/INT32-C.+Ensure+that+operations+on+signed+integers+do+not+result+in+overflow

Signed overflow is undefined behavior; unsigned wraps silently. Use `size_t` for sizes and indices, check ranges before arithmetic on untrusted values, use `__builtin_add_overflow` (GCC/Clang) or explicit checks, and enable `-Wconversion -Wsign-compare`.

## format-string-safety: Never pass user data as a format string
tags: c, printf, format string, security, vulnerability, logging
keywords: printf(user_input), %n
refs: https://wiki.sei.cmu.edu/confluence/display/c/FIO30-C.+Exclude+user+input+from+format+strings

`printf(msg)` with attacker-controlled `msg` can read and write memory via `%x`/`%n`. Always use a literal format: `printf("%s", msg)`. Compile with `-Wformat -Wformat-security`.

## initialize-variables: Initialize every variable before use
tags: c, uninitialized, undefined behavior, memset, struct initialization, warnings
keywords: random values, garbage
refs: https://wiki.sei.cmu.edu/confluence/display/c/EXP33-C.+Do+not+read+uninitialized+memory

Reading uninitialized automatic variables is undefined. Initialize at declaration (`struct cfg c = {0};`), use `calloc` when zeroed memory is required, and build with `-Wall -Wextra -Wuninitialized` plus MemorySanitizer or Valgrind in tests.

## const-and-restrict: Use const for read-only pointers in interfaces
tags: c, const, pointer, api design, restrict, header
keywords: function modifies input
refs: https://wiki.sei.cmu.edu/confluence/display/c/DCL00-C.+Const-qualify+immutable+objects

Declare pointer parameters a function only reads as `const T *`, so callers know their data is not modified and the compiler rejects accidental writes. Keep struct definitions private (opaque pointers) when callers do not need the layout.

## errno-and-return-codes: Check return values of every library call
tags: c, error handling, errno, return value, fopen, read, write, system calls
keywords: ignored return value, partial write
refs: https://wiki.sei.cmu.edu/confluence/display/c/ERR33-C.+Detect+and+handle+standard+library+errors

`fopen`, `read`, `write`, `fclose` and most POSIX calls signal failure in their return value; `write` and `read` may also transfer fewer bytes than requested, so loop until done. Read `errno` immediately after a failing call, and mark your own error-returning functions `__attribute__((warn_unused_result))`.
