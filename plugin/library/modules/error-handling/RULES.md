---
module: error-handling
capability: Error handling and resilience in application code
technologies:
applies: error handling, exceptions, retries, validation, failure, logging errors
checked_against: OWASP Error Handling Cheat Sheet, AWS Builders' Library, language documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## fail-fast-validation: Validate inputs at boundaries and fail fast with clear errors
tags: error handling, validation, fail fast, preconditions, boundaries, error messages
keywords: error surfaced far from cause
refs: https://martinfowler.com/ieeeSoftware/failFast.pdf

Check arguments, configuration and external input where they enter the system and reject invalid values immediately with a message naming the field and the expectation. Errors detected late, far from their cause, are expensive to diagnose.

## never-swallow-errors: Never swallow errors silently
tags: error handling, swallowed exceptions, empty catch, silent failure, logging
keywords: catch and ignore, error disappeared
refs: https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html

An empty `catch`/`except` hides failures until data is wrong. Either handle the error meaningfully (retry, fallback, user message), or let it propagate. If you deliberately ignore one, narrow the type and comment why.

## preserve-error-context: Wrap errors with context and keep the original cause
tags: error handling, error wrapping, cause, stack trace, context, debugging
keywords: generic error message, lost stack trace
refs: https://go.dev/blog/go1.13-errors

When re-raising, add what the code was doing (`loading invoice 42 from billing API`) and chain the original (`raise ... from err`, `%w`, `new Error(msg, { cause })`, Java exception cause). Errors without context or with the cause dropped turn minutes of debugging into hours.

## user-vs-internal-errors: Separate user-facing messages from internal details
tags: error handling, error messages, information disclosure, stack traces, user experience, security
keywords: stack trace shown to user
refs: https://owasp.org/www-community/Improper_Error_Handling

Show users a helpful, generic message with a correlation ID; log the full internal detail server-side. Stack traces, SQL errors and file paths in responses reveal internals to attackers and confuse users.

## expected-vs-unexpected: Model expected failures explicitly; let bugs crash loudly
tags: error handling, expected errors, result types, exceptions, domain errors, bugs
keywords: exceptions for control flow
refs: https://learn.microsoft.com/en-us/dotnet/standard/exceptions/best-practices-for-exceptions

"Not found", "insufficient funds" and validation failures are normal outcomes: represent them as domain errors or result types that callers must handle. Programming errors (null dereference, broken invariants) should fail loudly at a top-level handler that logs, reports and returns a 500, not be caught and patched over locally.

## cleanup-on-failure: Release resources and roll back partial work on every failure path
tags: error handling, cleanup, finally, rollback, resource leak, transactions, compensation
keywords: half finished operation left behind
refs: https://docs.python.org/3/reference/compound_stmts.html#the-try-statement

Use `finally`, `with`/`using`/`defer`, and transactions so failures do not leak connections or leave half-written state. For multi-step operations across systems that cannot share a transaction, define compensating actions (refund, release reservation) and run them on failure.

## top-level-handler: Have one top-level error handler per entry point
tags: error handling, global handler, middleware, crash reporting, workers, entry points
keywords: unhandled exception killed worker
refs: https://docs.sentry.io/platforms/python/

Every entry point (HTTP middleware, queue consumer loop, CLI main, scheduled job) needs one handler that logs the error with context, reports it to error tracking, returns or records an appropriate failure, and for workers decides whether to retry or dead-letter the message.
