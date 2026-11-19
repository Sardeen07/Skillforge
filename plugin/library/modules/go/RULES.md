---
module: go
capability: Go concurrency, errors and services
technologies: go
applies: go, golang, goroutine, channel, context, module
checked_against: Effective Go, Go standard library docs (Go 1.23)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## wrap-errors: Wrap errors with %w and inspect with errors.Is/As
tags: go, error handling, errors is, errors as, wrap, fmt errorf, sentinel errors
keywords: err == ErrNotFound fails, lost context
refs: https://go.dev/blog/go1.13-errors

Add context when returning: `return fmt.Errorf("load config %s: %w", path, err)`. Compare with `errors.Is(err, fs.ErrNotExist)` and extract types with `errors.As`, never with `==` on wrapped errors or string matching. Handle each error once: either log it or return it, not both.

## context-propagation: Pass context.Context as the first parameter and honor cancellation
tags: go, context, cancellation, timeout, deadline, http, database
keywords: request cancelled but work continues, context.Background in handler
refs: https://pkg.go.dev/context

Accept `ctx context.Context` as the first argument of every function that does I/O, pass the request's context (`r.Context()`) down, and use `db.QueryContext`/`http.NewRequestWithContext`. Set deadlines with `context.WithTimeout` and always `defer cancel()`. Do not store contexts in structs.

## goroutine-leaks: Give every goroutine a way to exit
tags: go, goroutine, leak, channel, select, done, errgroup, waitgroup
keywords: goroutines grow forever, blocked send
refs: https://pkg.go.dev/golang.org/x/sync/errgroup

A goroutine blocked forever on a channel send or receive is a leak. Select on `ctx.Done()` alongside channel operations, make channels buffered when a sender must not block on an abandoned receiver, and manage groups with `errgroup.WithContext` (first error cancels the rest) or `sync.WaitGroup`.

## data-races: Run tests with -race and protect shared state
tags: go, race condition, data race, mutex, atomic, race detector, concurrency, map
keywords: concurrent map writes fatal error
refs: https://go.dev/doc/articles/race_detector

Maps and most types are not safe for concurrent writes ("fatal error: concurrent map writes"). Guard shared state with `sync.Mutex`/`RWMutex`, use `sync/atomic` types for counters, or confine state to one goroutine and communicate over channels. Run `go test -race ./...` in CI.

## loop-variable-capture: Know Go 1.22 loop-variable semantics
tags: go, loop variable, closure, goroutine, for range, go 1.22
keywords: all goroutines see last value
refs: https://go.dev/blog/loopvar-preview

Since Go 1.22 each loop iteration has its own variable, so closures and goroutines capture the expected value. Modules declaring an older `go` version in `go.mod` keep the old shared-variable behavior; there, copy the variable (`v := v`) or pass it as an argument.

## http-server-timeouts: Set timeouts on http.Server and http.Client
tags: go, http, timeout, server, client, slowloris, net/http
keywords: http.Get hangs, DefaultClient no timeout
refs: https://pkg.go.dev/net/http#Server

`http.ListenAndServe` and `http.DefaultClient` have no timeouts, so slow clients or servers hold connections forever. Configure `http.Server{ReadHeaderTimeout, ReadTimeout, WriteTimeout, IdleTimeout}` and `http.Client{Timeout: 10 * time.Second}` (or per-request contexts). Always `defer resp.Body.Close()` and drain the body to reuse connections.

## defer-in-loops: Do not defer inside long loops
tags: go, defer, loop, resource leak, file handles, close
keywords: too many open files
refs: https://go.dev/ref/spec#Defer_statements

Deferred calls run when the function returns, not at the end of each loop iteration, so `defer f.Close()` inside a loop over thousands of files keeps them all open. Move the loop body into a helper function, or close explicitly.

## interfaces-small: Define small interfaces where they are used
tags: go, interface, api design, testing, dependency injection, accept interfaces
keywords: large interface, mock everything
refs: https://go.dev/doc/effective_go#interfaces

Declare interfaces in the consuming package with only the methods it needs (`type Store interface { Get(ctx, id) (User, error) }`) and return concrete types from constructors. Small interfaces make fakes trivial in tests and avoid coupling to a provider's full API.

## nil-interface-trap: Do not return a typed nil pointer as an error interface
tags: go, nil, interface, error, typed nil, pointer
keywords: err != nil but value is nil
refs: https://go.dev/doc/faq#nil_error

An interface holding a nil `*MyError` is not `nil`, so `return p` where `p` is a nil pointer of a concrete error type makes callers see a non-nil error. Return the literal `nil` for success, and declare return types as `error`, not concrete error pointers.

## slices-and-maps-gotchas: Beware slice aliasing and preallocate capacity
tags: go, slice, append, aliasing, capacity, make, map, performance
keywords: append modified other slice
refs: https://go.dev/blog/slices-intro

Slices share backing arrays: appending to a subslice can overwrite the parent's elements. Copy (`slices.Clone`) before handing out slices you will modify, use full slice expressions `s[a:b:b]` to cap capacity, and preallocate with `make([]T, 0, n)` / `make(map[K]V, n)` when the size is known.

## table-driven-tests: Write table-driven tests with t.Run subtests
tags: go, testing, table driven, t run, subtests, parallel, testify
keywords: repetitive tests
refs: https://go.dev/wiki/TableDrivenTests

Express cases as a slice of structs and run each with `t.Run(tc.name, ...)`, so failures name the case and `go test -run 'TestX/case'` targets one. Use `t.Helper()` in assertion helpers, `t.Cleanup` for teardown, and `t.Parallel()` only for tests without shared state.

## structured-logging-slog: Use log/slog for structured logs
tags: go, logging, slog, structured logging, json logs, observability
keywords: log.Printf, unparseable logs
refs: https://pkg.go.dev/log/slog

Use `log/slog` (Go 1.21+) with a JSON handler in production: `slog.Info("order placed", "order_id", id, "amount", amt)`. Key-value attributes are queryable in log systems; pass a request-scoped logger via context or dependency injection.

## go-sql-rows-close: Close rows, check rows.Err and reuse the sql.DB pool
tags: go, database sql, rows close, connection pool, sql db, leaks, error handling
keywords: too many connections, rows not closed
refs: https://go.dev/doc/database/querying

Create one `*sql.DB` per database at startup (it is a pool) and configure `SetMaxOpenConns`, `SetMaxIdleConns` and `SetConnMaxLifetime`. After `db.QueryContext`, `defer rows.Close()` and check `rows.Err()` after the loop; an unclosed `Rows` holds a connection until garbage collection.
