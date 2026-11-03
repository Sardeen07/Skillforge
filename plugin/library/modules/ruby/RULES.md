---
module: ruby
capability: Ruby and Rails correctness, security and performance
technologies: ruby
applies: ruby, rails, activerecord, rspec, sidekiq
checked_against: Ruby 3.3 documentation and Rails 7.2 guides
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## activerecord-n-plus-one: Preload associations with includes
tags: ruby, rails, activerecord, n+1, includes, preload, eager loading, performance
keywords: query per row, bullet gem, strict_loading
refs: https://guides.rubyonrails.org/active_record_querying.html#eager-loading-associations

Iterating `posts.each { |p| p.author.name }` runs one query per post. Use `Post.includes(:author)` (or `preload`/`eager_load`), and enable `strict_loading` on models or relations in development to raise on lazy loads.

## strong-parameters: Permit attributes explicitly with strong parameters
tags: ruby, rails, strong parameters, mass assignment, permit, security, controller
keywords: params.permit!, admin flag
refs: https://guides.rubyonrails.org/action_controller_overview.html#strong-parameters

Never pass raw `params` to `create`/`update`. Use `params.require(:user).permit(:name, :email)` (or `params.expect` in Rails 8) and never `permit!`. Attributes such as `role` or `admin` must be set only by code that checks authorization.

## sql-injection-rails: Use bound conditions, never string interpolation in queries
tags: ruby, rails, sql injection, where, activerecord, security, find_by_sql
keywords: where("name = '#{params[:name]}'")
refs: https://guides.rubyonrails.org/security.html#sql-injection

`where("email = '#{params[:email]}'")` is injectable. Use hash conditions (`where(email: params[:email])`) or placeholders (`where("created_at > ?", time)`). For dynamic `order` columns, map user input through an allowlist; `sanitize_sql_like` escapes `LIKE` wildcards.

## background-jobs-idempotent: Make background jobs idempotent and pass IDs, not objects
tags: ruby, rails, sidekiq, active job, background jobs, idempotency, retries
keywords: job ran twice, serialized record stale
refs: https://github.com/sidekiq/sidekiq/wiki/Best-Practices

Job systems retry on failure, so a job may run more than once: design it to be safe to repeat (check state, use unique constraints). Enqueue simple arguments (record IDs) and reload the record inside the job; enqueue after the transaction commits (`after_commit`) so the job never sees missing rows.

## frozen-string-literals: Enable frozen string literals and avoid mutating shared strings
tags: ruby, frozen string literal, string, mutation, performance, memory
keywords: can't modify frozen String
refs: https://docs.ruby-lang.org/en/3.3/syntax/comments_rdoc.html#label-frozen_string_literal+Directive

Add `# frozen_string_literal: true` to files (RuboCop enforces it) so literal strings are deduplicated and cannot be mutated by accident. Build strings with `+"" <<` or `String.new` when mutation is intended.

## database-constraints-rails: Back model validations with database constraints
tags: ruby, rails, validations, uniqueness, database constraints, migrations, race condition
keywords: duplicate records despite validates uniqueness
refs: https://guides.rubyonrails.org/active_record_validations.html#uniqueness

`validates :email, uniqueness: true` checks then inserts, so concurrent requests create duplicates. Add a unique index in a migration and handle `ActiveRecord::RecordNotUnique`. Likewise pair `presence` with `null: false` and associations with foreign keys.

## rspec-focused-tests: Write fast, isolated RSpec tests with factories built, not created
tags: ruby, rspec, testing, factory bot, build stubbed, slow tests, let
keywords: slow test suite, create everywhere
refs: https://rspec.info/features/3-13/rspec-core/

Use `build`/`build_stubbed` instead of `create` when persistence is not under test, prefer `let` over instance variables, keep one behavior per example, and avoid `allow_any_instance_of`. Persisted factories in every spec are the most common cause of slow Rails suites.

## safe-navigation-and-nil: Handle nil explicitly at boundaries
tags: ruby, nil, safe navigation, nomethoderror, fetch, hash, presence
keywords: undefined method for nil:NilClass
refs: https://docs.ruby-lang.org/en/3.3/Hash.html#method-i-fetch

Use `hash.fetch(:key)` when the key must exist (it raises a clear `KeyError`), `fetch(:key, default)` for defaults, and `&.` only where `nil` is genuinely acceptable; long `&.` chains hide the real source of a missing value.
