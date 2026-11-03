---
module: testing
capability: Test strategy, isolation, mocks and reliability
technologies:
applies: testing, unit test, integration test, mock, flaky, coverage, e2e
checked_against: martinfowler.com testing articles, Google Testing Blog, pytest and Jest documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## test-behavior-not-implementation: Test observable behavior through public interfaces
tags: testing, unit tests, behavior, implementation details, refactoring, brittle tests
keywords: tests break on every refactor
refs: https://testing.googleblog.com/2013/08/testing-on-toilet-test-behavior-not.html

Assert on outputs, returned values, persisted state and emitted events, not on private methods or the sequence of internal calls. Tests coupled to implementation fail on harmless refactors and pass on real regressions.

## mock-boundaries-only: Mock at system boundaries, not your own internals
tags: testing, mocks, test doubles, fakes, stubs, boundaries, integration tests
keywords: everything mocked, tests pass but prod fails
refs: https://martinfowler.com/articles/mocksArentStubs.html

Replace things that are slow, nondeterministic or external (network APIs, clock, randomness, payment providers) with fakes or stubs; use real implementations of your own code and, where practical, real databases in containers. Over-mocked tests verify your assumptions about collaborators, not the system.

## testing-pyramid-balance: Balance fast unit tests with a few high-value integration and end-to-end tests
tags: testing, test pyramid, integration tests, e2e tests, unit tests, test strategy, ci speed
keywords: only e2e tests, slow suite
refs: https://martinfowler.com/articles/practical-test-pyramid.html

Most tests should be fast and focused; integration tests verify contracts with real dependencies (database, queue, HTTP); a small number of end-to-end tests cover critical user journeys. A suite dominated by slow UI tests is flaky and slow; one with only unit tests misses wiring errors.

## deterministic-tests: Make tests deterministic: control time, randomness, ordering and concurrency
tags: testing, flaky tests, determinism, time, random seed, sleep, race conditions, test isolation
keywords: passes locally fails in ci, sleep in tests
refs: https://testing.googleblog.com/2020/12/test-flakiness-one-of-main-challenges.html

Inject a clock instead of reading the current time, seed or inject randomness, never depend on test execution order or shared mutable state, and wait for conditions (poll with a timeout) instead of fixed `sleep`s. Each test sets up and cleans up its own data.

## regression-test-first: Reproduce a bug with a failing test before fixing it
tags: testing, regression test, bug fix, tdd, reproduction, debugging
keywords: bug came back
refs: https://martinfowler.com/bliki/TestDrivenDevelopment.html

Write a test that fails because of the reported bug, watch it fail for the right reason, then fix the code and watch it pass. The test documents the bug and prevents it from returning.

## edge-cases-and-boundaries: Cover boundaries, empty inputs and error paths
tags: testing, edge cases, boundary values, error handling, null, empty, property based testing
keywords: off by one, crash on empty list
refs: https://hypothesis.readthedocs.io/en/latest/

Test empty, single-element and maximum-size inputs, boundary values (0, -1, limits), invalid input, and failure of each dependency. Property-based testing (Hypothesis, fast-check, jqwik) generates such cases and shrinks failures to minimal examples.

## coverage-as-signal: Use coverage to find untested code, not as a target
tags: testing, code coverage, mutation testing, quality metrics, assertions
keywords: 100 percent coverage still buggy
refs: https://martinfowler.com/bliki/TestCoverage.html

Coverage shows what code never runs under test; it does not show that behavior is asserted. Review uncovered critical paths, avoid assertion-free tests that inflate numbers, and use mutation testing on core logic to check that tests actually detect changes.

## test-data-builders: Build test data with factories that state only what matters
tags: testing, test data, factories, fixtures, builders, readability, maintainability
keywords: giant fixture files
refs: https://martinfowler.com/bliki/ObjectMother.html

Use builders or factories with sensible defaults so each test sets only the fields relevant to its assertion (`make_order(status="shipped")`). Large shared fixtures couple unrelated tests and hide which data matters.

## contract-tests: Verify service integrations with contract tests
tags: testing, contract testing, consumer driven contracts, pact, api compatibility, microservices
keywords: provider change broke consumer
refs: https://martinfowler.com/bliki/ContractTest.html

When services evolve independently, check that a provider still satisfies what its consumers rely on with consumer-driven contract tests (e.g. Pact) or schema compatibility checks in CI, rather than relying solely on slow shared end-to-end environments.

## test-database-real: Test data-access code against the real database engine
tags: testing, database tests, testcontainers, sqlite vs postgres, integration tests, migrations
keywords: tests use sqlite prod uses postgres
refs: https://testcontainers.com/guides/introducing-testcontainers/

SQL dialects, constraints, locking and JSON behavior differ between engines, so tests on an in-memory substitute miss real bugs. Run repository tests against the same engine and version as production (Testcontainers, a CI service container), apply real migrations, and isolate tests with transactions rolled back after each test or per-test schemas.
