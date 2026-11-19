---
module: code-quality
capability: Clean code, refactoring and code review
technologies:
applies: refactoring, clean code, code review, readability, naming, technical debt
checked_against: Refactoring (2nd ed.) catalog at refactoring.com, Google engineering practices (code review)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## refactor-in-small-steps: Refactor in small, behavior-preserving steps under tests
tags: refactoring, small steps, tests, behavior preserving, legacy code, characterization tests
keywords: big rewrite broke everything
refs: https://refactoring.com/

Before refactoring, make sure tests cover the behavior (add characterization tests to legacy code that has none). Then change structure in small steps (rename, extract function, move) running tests after each, and keep refactoring commits separate from behavior changes so reviews and reverts stay simple.

## intention-revealing-names: Name things for what they mean in the domain
tags: clean code, naming, readability, variables, functions, domain language
keywords: data, tmp, handle, manager, doStuff
refs: https://google.github.io/styleguide/pyguide.html#316-naming

Use names that say what a value is or what a function does (`overdue_invoices`, `charge_customer`), consistent with the domain's vocabulary. Replace magic numbers with named constants, and booleans with names that read as questions (`is_active`, `has_access`).

## small-functions-guard-clauses: Keep functions short and flatten nesting with guard clauses
tags: clean code, functions, nesting, guard clauses, early return, complexity, readability
keywords: arrow code, deeply nested ifs
refs: https://refactoring.com/catalog/replaceNestedConditionalWithGuardClauses.html

Handle invalid and special cases first with early returns, so the main path reads straight down. Extract blocks that need a comment into well-named functions, and keep each function at one level of abstraction.

## remove-duplication-wisely: Remove duplicated knowledge, not coincidental similarity
tags: clean code, dry, duplication, abstraction, coupling, wrong abstraction
keywords: shared helper with many flags
refs: https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction

Deduplicate when two places encode the same business rule and must change together. Code that merely looks similar but changes for different reasons should stay separate; a premature shared abstraction accumulates parameters and conditionals. Wait for the third occurrence when unsure.

## review-checklist: Review for correctness, design and tests before style
tags: code review, pull request, review checklist, correctness, tests, security, maintainability
keywords: nitpicks only in review
refs: https://google.github.io/eng-practices/review/reviewer/looking-for.html

In review, check first that the change does what it claims (including edge cases and error paths), fits the design, is covered by tests that would fail without it, and has no security or data-loss risk. Leave formatting to automated tools, label optional comments as such, and keep pull requests small enough to review in one sitting.

## comments-explain-why: Write comments that explain why, and keep them true
tags: clean code, comments, documentation, readability, technical debt, todo
keywords: comment says what code does, outdated comment
refs: https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings

Code shows what happens; comments should record why (constraints, trade-offs, links to incidents or specs) and public API contracts. Delete commented-out code (version control keeps it), update comments with the code, and give TODOs an owner or ticket.

## make-illegal-states-unrepresentable: Encode invariants in types, not comments
tags: clean code, types, invariants, domain modeling, enums, value objects, refactoring
keywords: status string compared everywhere, boolean flags combinations
refs: https://fsharpforfunandprofit.com/posts/designing-with-types-making-illegal-states-unrepresentable/

Replace combinations of booleans and nullable fields that can contradict each other with enums, sum types or value objects whose constructors validate (an `EmailAddress` type, an `OrderStatus` enum with allowed transitions). Each invariant is then checked once, at creation, rather than defensively everywhere.

## dead-code-and-flags: Delete dead code and expired feature flags
tags: clean code, dead code, feature flags, technical debt, maintainability, unused code
keywords: if False, flag always on
refs: https://martinfowler.com/articles/feature-toggles.html

Unused functions, branches behind permanently-on flags and commented-out blocks still cost reading time and hide bugs. Give each feature flag an owner and removal date, delete the losing branch once a flag is fully rolled out, and use coverage or static analysis to find unreachable code.

## consistent-formatting-automation: Automate formatting and linting
tags: code review, formatting, linting, prettier, black, ruff, eslint, pre commit
keywords: review comments about whitespace
refs: https://pre-commit.com/

Run a formatter (Black/Ruff, Prettier, gofmt, rustfmt) and a linter automatically in pre-commit hooks and CI, so style never appears in code review and diffs show only meaningful changes. Adopt the formatter's defaults rather than debating options.
