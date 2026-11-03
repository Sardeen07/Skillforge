---
module: fastapi
capability: FastAPI correctness, async and validation
technologies: fastapi
applies: fastapi, pydantic, async, dependency injection, uvicorn
checked_against: FastAPI 0.115 and Pydantic 2 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## async-def-vs-def: Use def for blocking endpoints and async def only with async I/O
tags: fastapi, async, def, blocking, threadpool, event loop, performance
keywords: requests slow under load, sync db call in async def
refs: https://fastapi.tiangolo.com/async/

FastAPI runs plain `def` endpoints in a thread pool but `async def` endpoints on the event loop. A blocking call (synchronous DB driver, `requests`, `time.sleep`) inside `async def` stalls every request. Use `async def` only when everything awaited is async; otherwise declare the endpoint `def`.

## pydantic-models-io: Declare request and response models
tags: fastapi, pydantic, response model, validation, serialization, data leakage
keywords: password hash returned, returning ORM object
refs: https://fastapi.tiangolo.com/tutorial/response-model/

Accept bodies as Pydantic models (validated automatically, 422 on bad input) and set `response_model` (or a return annotation) to an output schema, so internal fields such as password hashes are never serialized. Use separate `UserCreate`/`UserOut` models.

## dependencies-for-resources: Use dependencies with yield for sessions and auth
tags: fastapi, dependency injection, depends, database session, yield, authentication
keywords: session not closed, global db session
refs: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/

Provide DB sessions, clients and the current user through `Depends`. A dependency that `yield`s gets cleanup after the response. Dependencies are cached per request, so `get_current_user` runs once even if several dependencies need it.

## lifespan-shared-clients: Create shared clients in lifespan, not per request
tags: fastapi, lifespan, startup, httpx, connection pool, shutdown, resources
keywords: new client per request, on_event deprecated
refs: https://fastapi.tiangolo.com/advanced/events/

Create expensive shared resources (an `httpx.AsyncClient`, a DB engine, a model) once in the `lifespan` context manager and close them on shutdown. `@app.on_event` is deprecated. Per-request clients waste connections and add latency.

## http-exceptions-and-status: Raise HTTPException with precise status codes
tags: fastapi, httpexception, status codes, error handling, rest, exception handlers
keywords: returns 200 with error, 500 on not found
refs: https://fastapi.tiangolo.com/tutorial/handling-errors/

Raise `HTTPException(status_code=404, detail="Order not found")` for expected errors, set `status_code=201` on creation endpoints, and register exception handlers for domain exceptions so business code does not import web types. Do not leak internal exception messages.

## background-tasks-limits: Use BackgroundTasks only for small fire-and-forget work
tags: fastapi, background tasks, task queue, celery, reliability, retries
keywords: email lost on restart, long job in background task
refs: https://fastapi.tiangolo.com/tutorial/background-tasks/

`BackgroundTasks` run in the same process after the response; they are lost on restart and have no retries. For work that must happen (emails, payments, reports), enqueue to a durable queue (Celery, RQ, arq, a database-backed queue).

## settings-pydantic: Load configuration with pydantic-settings
tags: fastapi, configuration, settings, environment variables, pydantic settings, secrets
keywords: os.environ scattered
refs: https://fastapi.tiangolo.com/advanced/settings/

Define a `Settings(BaseSettings)` class, load it once (cache with `@lru_cache`), inject it via `Depends`, and override it in tests. Typed settings fail fast on missing values; use `SecretStr` so secrets are not printed.
