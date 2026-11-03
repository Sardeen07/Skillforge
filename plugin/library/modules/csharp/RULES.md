---
module: csharp
capability: C# and .NET async, resources and data access
technologies: csharp
applies: csharp, dotnet, async, linq, entity framework, asp.net
checked_against: Microsoft Learn .NET 8 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## async-all-the-way: Never block on async code with .Result or .Wait()
tags: csharp, async await, task, deadlock, thread pool starvation, result, wait
keywords: .Result deadlock, GetAwaiter().GetResult()
refs: https://learn.microsoft.com/en-us/archive/msdn-magazine/2013/march/async-await-best-practices-in-asynchronous-programming

Blocking on tasks (`.Result`, `.Wait()`, `GetAwaiter().GetResult()`) can deadlock in UI or legacy ASP.NET contexts and starves the thread pool in ASP.NET Core. Make callers `async` up the chain. Avoid `async void` except for event handlers; return `Task`/`ValueTask`.

## cancellation-tokens: Accept and pass CancellationToken
tags: csharp, cancellationtoken, async, cancellation, timeout, httpclient, ef core
keywords: request aborted but query continues
refs: https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads

Accept a `CancellationToken` in async methods and pass it to every awaited call (`HttpClient.GetAsync(url, ct)`, `ToListAsync(ct)`). In ASP.NET Core, bind the action parameter or use `HttpContext.RequestAborted` so abandoned requests stop their work.

## httpclient-lifetime: Reuse HttpClient via IHttpClientFactory
tags: csharp, httpclient, socket exhaustion, ihttpclientfactory, dns, dependency injection
keywords: new HttpClient per request
refs: https://learn.microsoft.com/en-us/dotnet/fundamentals/networking/http/httpclient-guidelines

Creating and disposing an `HttpClient` per request exhausts sockets (TIME_WAIT); a single static one ignores DNS changes. Register clients with `IHttpClientFactory` (`services.AddHttpClient<T>()`) or use one long-lived `HttpClient` with `SocketsHttpHandler.PooledConnectionLifetime` set.

## dispose-pattern: Dispose IDisposable and IAsyncDisposable with using
tags: csharp, idisposable, using, dispose, resource leak, iasyncdisposable
keywords: connection not closed, file locked
refs: https://learn.microsoft.com/en-us/dotnet/standard/garbage-collection/using-objects

Wrap disposable objects in `using var x = ...;` or `await using` for async-disposable ones, so they are released on every path. Do not dispose objects owned by the DI container, and do not hold `DbContext` beyond a request scope.

## ef-core-queries: Project, filter on the server and use AsNoTracking for reads
tags: csharp, entity framework, ef core, linq, n+1, include, asnotracking, performance
keywords: ToList then Where, client evaluation, lazy loading
refs: https://learn.microsoft.com/en-us/ef/core/performance/efficient-querying

Keep `Where`/`Select` before `ToListAsync()` so they translate to SQL; project only needed columns with `Select`; load related data with `Include` (or split queries for large graphs) instead of lazy loading in loops; and use `AsNoTracking()` for read-only queries.

## nullable-reference-types: Enable nullable reference types and treat warnings as errors
tags: csharp, nullable, null reference, compiler warnings, nullreferenceexception
keywords: Object reference not set to an instance
refs: https://learn.microsoft.com/en-us/dotnet/csharp/nullable-references

Set `<Nullable>enable</Nullable>` and `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` (at least for nullable warnings), annotate `T?` where null is valid, and validate external input with `ArgumentNullException.ThrowIfNull`. Avoid the `!` null-forgiving operator except where you can prove non-null.

## linq-deferred-execution: Remember LINQ is deferred; materialize once
tags: csharp, linq, deferred execution, ienumerable, multiple enumeration, performance
keywords: query executed twice
refs: https://learn.microsoft.com/en-us/dotnet/standard/linq/deferred-execution-lazy-evaluation

A LINQ query over `IEnumerable`/`IQueryable` runs each time it is enumerated: calling `Count()` then `foreach` hits the database twice. Materialize with `ToList()`/`ToArray()` when the result is used more than once, and do not capture loop-changing variables in deferred queries.

## options-and-secrets: Bind configuration with IOptions and keep secrets out of appsettings
tags: csharp, configuration, ioptions, secrets, user secrets, key vault, appsettings
keywords: connection string committed
refs: https://learn.microsoft.com/en-us/aspnet/core/fundamentals/configuration/options

Bind settings to typed classes with `services.AddOptions<T>().Bind(...).ValidateDataAnnotations().ValidateOnStart()`, so misconfiguration fails at startup. Keep secrets in User Secrets for development and Key Vault or environment variables in production, never in committed `appsettings.json`.

## structured-logging-dotnet: Use message templates in ILogger, not interpolated strings
tags: csharp, logging, ilogger, structured logging, serilog, message template
keywords: $"..." in LogInformation
refs: https://learn.microsoft.com/en-us/dotnet/core/extensions/logging#log-message-template

Write `logger.LogInformation("Order {OrderId} placed", id)`, not `$"Order {id} placed"`: templates keep `OrderId` as a queryable field and skip formatting when the level is disabled. Use `LoggerMessage` source generators on hot paths.
