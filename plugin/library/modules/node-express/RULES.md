---
module: node-express
capability: Node.js and Express services in production
technologies: node, express
applies: node, express, middleware, event loop, npm, server
checked_against: Node.js 22 documentation and Express 5 guides
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## async-error-handling-express: Forward async errors to the error middleware
tags: express, node, error handling, async, middleware, unhandled rejection, next
keywords: request hangs on error, async route throws
refs: https://expressjs.com/en/guide/error-handling.html

Express 5 forwards rejected promises from async handlers to error middleware; Express 4 does not, and the request hangs or the process crashes. On Express 4 wrap handlers (`(req, res, next) => fn(req, res, next).catch(next)`) or upgrade. Register one error handler with four arguments `(err, req, res, next)` last; it logs and returns a generic message without stack traces.

## dont-block-event-loop: Keep CPU-heavy and synchronous work off the event loop
tags: node, event loop, blocking, sync fs, crypto, json parse, worker threads, latency
keywords: readFileSync in handler, all requests slow
refs: https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop

One slow synchronous operation blocks every request. Avoid `*Sync` APIs in request paths, use async `crypto` (`scrypt`, not `scryptSync`), cap input sizes before `JSON.parse` or regex matching, and move CPU-heavy work to `worker_threads` or a separate service. Monitor event-loop delay with `perf_hooks.monitorEventLoopDelay`.

## validate-request-input: Validate body, params and query at the edge
tags: express, node, validation, input, zod, joi, schema, security
keywords: req.body trusted, type confusion
refs: https://cheatsheetseries.owasp.org/cheatsheets/Nodejs_Security_Cheat_Sheet.html

Treat `req.body`, `req.query` and `req.params` as untrusted: query values may be strings, arrays or objects (`?id[$ne]=1` reaches NoSQL queries). Validate with a schema (zod, joi, ajv) and pass only the parsed result onward. Limit body size with `express.json({ limit: '100kb' })`.

## security-middleware: Set security headers, rate limits and trust proxy correctly
tags: express, node, helmet, rate limiting, security headers, cors, trust proxy
keywords: x-powered-by, brute force login
refs: https://expressjs.com/en/advanced/best-practice-security.html

Use `helmet()` for security headers, disable `x-powered-by`, configure CORS with an explicit origin allowlist (never reflect any origin with credentials), and rate-limit authentication endpoints. Behind a load balancer set `app.set('trust proxy', 1)` (the exact hop count), or `req.ip` and rate limiting see only the proxy.

## graceful-shutdown: Shut down gracefully on SIGTERM
tags: node, graceful shutdown, sigterm, kubernetes, server close, connections, deploy
keywords: dropped requests during deploy
refs: https://nodejs.org/api/process.html#signal-events

On `SIGTERM`, stop accepting connections (`server.close()`), let in-flight requests finish within a deadline, close database pools and queues, then exit. Fail readiness checks first so the load balancer stops routing new traffic. Without this, every deploy drops requests.

## env-config-validation: Load and validate configuration once at startup
tags: node, configuration, environment variables, dotenv, secrets, startup validation
keywords: undefined env var at runtime
refs: https://nodejs.org/en/learn/command-line/how-to-read-environment-variables-from-nodejs

Read `process.env` in one config module at startup, validate required values and types with a schema, and fail fast with a clear error. Do not commit `.env` files with real secrets; `node --env-file=.env` (Node 20.6+) loads local files without extra dependencies.

## connection-pooling-node: Reuse database and HTTP connections
tags: node, connection pool, database, http agent, keep alive, pg pool, performance
keywords: new client per request, too many connections
refs: https://node-postgres.com/features/pooling

Create one database pool per process at startup and reuse it; release clients in `finally`. Reuse keep-alive agents for outbound HTTP (the default in Node 19+ and in `fetch`). A connection per request adds latency and exhausts database connection limits.

## stream-large-payloads: Stream large files and responses instead of buffering
tags: node, streams, pipeline, backpressure, memory, file upload, large response
keywords: out of memory reading file
refs: https://nodejs.org/api/stream.html#streampipelinesource-transforms-destination-callback

Reading whole files or responses into memory spikes memory and latency. Use streams composed with `pipeline()` from `stream/promises`, which handles backpressure and errors; parse large uploads with a streaming multipart parser and enforce size limits.

## dependency-hygiene-npm: Lock, audit and minimize npm dependencies
tags: node, npm, dependencies, lock file, npm audit, supply chain, npm ci
keywords: npm install in ci
refs: https://docs.npmjs.com/cli/v10/commands/npm-ci

Commit the lock file, install in CI with `npm ci`, run `npm audit` or a dependency scanner, review new transitive dependencies, and prefer the platform (`fetch`, `crypto.randomUUID`, `node:test`) over small packages.

## process-crash-handling: Crash on unknown errors and let the supervisor restart
tags: node, uncaughtexception, unhandledrejection, process manager, crash, restart, resilience
keywords: catch uncaughtException and continue
refs: https://nodejs.org/api/process.html#warning-using-uncaughtexception-correctly

After an `uncaughtException` the process may be in an undefined state. Log it, flush, and exit non-zero; let the orchestrator (Kubernetes, systemd, PM2) restart it. Do not use the handler to keep serving.
