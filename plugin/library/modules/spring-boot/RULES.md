---
module: spring-boot
capability: Spring Boot transactions, JPA and configuration
technologies: spring
applies: spring, spring boot, jpa, hibernate, transactional, bean
checked_against: Spring Boot 3.3 and Spring Framework 6.1 reference documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## transactional-proxy-pitfalls: Know when @Transactional does not apply
tags: spring, transactional, proxy, self invocation, rollback, checked exception, jpa
keywords: transaction not rolled back, self call
refs: https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html

`@Transactional` works through a proxy: calls from another method of the same bean (self-invocation) and non-public methods bypass it. By default it rolls back only on unchecked exceptions; add `rollbackFor = Exception.class` when checked exceptions must roll back. Put transactions on the service layer, and keep remote calls outside them.

## jpa-n-plus-one: Fetch associations explicitly; avoid lazy loading in loops
tags: spring, jpa, hibernate, n+1, fetch join, entitygraph, lazy loading, performance
keywords: LazyInitializationException, open in view
refs: https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html#jpa.entity-graph

Accessing a lazy collection per entity in a loop issues one query each. Load what the use case needs with `JOIN FETCH` or `@EntityGraph`, or query DTO projections. Set `spring.jpa.open-in-view=false` so lazy loading cannot silently run during view rendering, and enable SQL logging in development to count queries.

## constructor-injection: Use constructor injection with final fields
tags: spring, dependency injection, constructor injection, autowired, field injection, testing
keywords: @Autowired on field, null in tests
refs: https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html

Inject dependencies through the constructor (no `@Autowired` needed with one constructor) into `final` fields. Field injection hides dependencies, allows partially constructed objects, and makes plain unit tests impossible without the container.

## configuration-properties: Bind configuration with @ConfigurationProperties and validate it
tags: spring, configuration, configurationproperties, validation, profiles, secrets
keywords: @Value scattered, missing property at runtime
refs: https://docs.spring.io/spring-boot/reference/features/external-config.html#features.external-config.typesafe-configuration-properties

Group settings in a `@ConfigurationProperties` record annotated `@Validated` with constraint annotations, so bad configuration fails at startup. Keep secrets in environment variables or a secret manager, not in committed `application.yml`.

## controller-advice-errors: Map exceptions to responses in one @RestControllerAdvice
tags: spring, error handling, controlleradvice, problem details, status codes, rest, validation
keywords: stack trace in response, 500 for validation error
refs: https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-ann-rest-exceptions.html

Handle domain and validation exceptions centrally with `@RestControllerAdvice` and return RFC 9457 `ProblemDetail` bodies with correct status codes. Validate request bodies with `@Valid`. Never return exception messages or stack traces to clients.

## actuator-security: Expose only necessary Actuator endpoints and secure them
tags: spring, actuator, health checks, security, endpoints, observability, heapdump
keywords: /actuator/env exposed, heapdump public
refs: https://docs.spring.io/spring-boot/reference/actuator/endpoints.html#actuator.endpoints.security

Endpoints such as `env`, `heapdump` and `configprops` reveal secrets. Expose only what you need (`management.endpoints.web.exposure.include=health,info,prometheus`), put management on a separate port or behind authentication, and use liveness/readiness health groups for Kubernetes probes.

## security-filter-chain: Configure Spring Security with explicit authorization rules
tags: spring, spring security, authorization, securityfilterchain, csrf, method security
keywords: permitAll everything, csrf disabled
refs: https://docs.spring.io/spring-security/reference/servlet/authorization/authorize-http-requests.html

Define a `SecurityFilterChain` bean that denies by default (`anyRequest().authenticated()`) and opens specific paths. Keep CSRF protection on for cookie-based sessions (disable only for stateless token APIs), and add `@PreAuthorize` checks on service methods for per-object rules.

## pool-and-timeouts-spring: Size the connection pool and set client timeouts
tags: spring, hikaricp, connection pool, timeouts, resttemplate, webclient, resilience
keywords: connection is not available, request timed out after 30000ms
refs: https://docs.spring.io/spring-boot/reference/data/sql.html#data.sql.datasource.connection-pool

HikariCP defaults to 10 connections; size `spring.datasource.hikari.maximum-pool-size` to the database's capacity divided across instances, not to the thread count. Set connect and read timeouts on `RestClient`/`WebClient` calls; the defaults can wait far too long and exhaust threads.
