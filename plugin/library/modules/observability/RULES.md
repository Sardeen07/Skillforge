---
module: observability
capability: Logging, metrics, tracing and alerting
technologies: observability
applies: logging, metrics, tracing, monitoring, alerting, opentelemetry, slo
checked_against: OpenTelemetry documentation, Google SRE book and workbook
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## structured-logs: Emit structured logs with correlation IDs
tags: observability, structured logging, json logs, correlation id, request id, trace id
keywords: grep through text logs, cannot follow a request
refs: https://opentelemetry.io/docs/concepts/signals/logs/

Log JSON (or logfmt) with consistent field names, a level, a timestamp, and a request/trace ID propagated through every service, so one request can be followed end to end. Log events and decisions, not every line; never log secrets, tokens or full personal data.

## red-use-metrics: Instrument rate, errors and duration for every service
tags: observability, metrics, red method, latency, error rate, throughput, prometheus, histograms
keywords: average latency looks fine
refs: https://sre.google/sre-book/monitoring-distributed-systems/

Expose request rate, error rate and latency histograms (not averages) per endpoint, plus saturation of key resources (pool usage, queue depth, CPU, memory). Report percentiles (p50/p95/p99) from histograms; averages hide tail latency.

## metric-cardinality: Keep metric label cardinality bounded
tags: observability, metrics, cardinality, labels, prometheus, cost, time series
keywords: metrics bill exploded, user_id label
refs: https://prometheus.io/docs/practices/naming/#labels

Every unique label combination is a separate time series. Never use unbounded values (user IDs, request IDs, raw URLs, emails) as labels; use route templates (`/orders/:id`) and put high-cardinality detail in logs or traces.

## distributed-tracing: Propagate trace context across services and async boundaries
tags: observability, distributed tracing, opentelemetry, trace context, spans, w3c traceparent
keywords: cannot tell which service is slow
refs: https://opentelemetry.io/docs/concepts/context-propagation/

Use OpenTelemetry auto-instrumentation for HTTP, gRPC and database clients, propagate W3C `traceparent` headers (including through message queues as message attributes), and add spans with attributes around significant internal work. Sample deliberately (keep errors and slow traces) to control cost.

## slo-based-alerting: Alert on user-facing symptoms against SLOs, not on every cause
tags: observability, alerting, slo, error budget, burn rate, on call, alert fatigue
keywords: paged for cpu at 80 percent, too many alerts
refs: https://sre.google/workbook/alerting-on-slos/

Define SLOs for what users experience (availability, latency) and page on error-budget burn rate (fast and slow windows). Cause-based signals (CPU, disk) belong on dashboards or tickets unless they predict imminent user impact. Every page must be actionable and link to a runbook.

## health-endpoints: Expose meaningful health and readiness endpoints
tags: observability, health check, readiness, liveness, dependencies, load balancer
keywords: health check always returns 200
refs: https://microservices.io/patterns/observability/health-check-api.html

A health endpoint that always returns 200 hides outages. Separate liveness (process is running) from readiness (can serve: required dependencies reachable, warmed up), keep them cheap, and never require authentication or expensive queries in liveness checks.

## error-tracking: Capture exceptions with context in an error tracker
tags: observability, error tracking, sentry, exceptions, release tracking, stack traces
keywords: users report errors we never see
refs: https://docs.sentry.io/product/issues/

Send unhandled exceptions (backend and frontend) to an error tracker with release version, environment, user/tenant ID (not personal data) and breadcrumbs, upload source maps for minified JavaScript, and triage new issues per release.

## logs-cost-retention: Control log volume with levels, sampling and retention
tags: observability, log volume, cost, sampling, retention, debug logs, log levels
keywords: logging bill too high
refs: https://opentelemetry.io/docs/concepts/sampling/

Default production to INFO, keep DEBUG switchable at runtime, sample high-volume success logs while keeping all errors, avoid logging large payloads, and set retention by usefulness (short for debug data, longer for audit logs that are legally required).
