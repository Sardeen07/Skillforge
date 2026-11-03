---
module: php
capability: Secure, typed modern PHP and Laravel
technologies: php
applies: php, laravel, composer, pdo, symfony
checked_against: PHP 8.3 manual, Laravel 11 documentation, OWASP cheat sheets
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## pdo-prepared-statements: Use prepared statements with bound parameters
tags: php, pdo, sql injection, prepared statements, mysqli, database, security
keywords: query string concatenation, $_GET in query
refs: https://www.php.net/manual/en/pdo.prepared-statements.php

Never interpolate request data into SQL. Use `$stmt = $pdo->prepare('SELECT * FROM users WHERE email = ?'); $stmt->execute([$email]);`. Set `PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION` and `PDO::ATTR_EMULATE_PREPARES => false`. Identifiers (column names for sorting) cannot be bound; map them through an allowlist.

## strict-types: Declare strict_types and type every signature
tags: php, strict types, type declarations, return types, phpstan, psalm, static analysis
keywords: "5 apples" + 1, type juggling
refs: https://www.php.net/manual/en/language.types.declarations.php#language.types.declarations.strict

Start files with `declare(strict_types=1);` so scalar parameters are not silently coerced, declare parameter, return and property types (including nullable and union types), and run PHPStan or Psalm at a high level in CI.

## password-hashing-php: Hash passwords with password_hash and verify with password_verify
tags: php, password, hashing, bcrypt, argon2, authentication, security
keywords: md5 password, sha1 password
refs: https://www.php.net/manual/en/function.password-hash.php

Use `password_hash($password, PASSWORD_DEFAULT)` (or `PASSWORD_ARGON2ID`) and `password_verify()`; call `password_needs_rehash()` on login to upgrade old hashes. Never use `md5`, `sha1` or unsalted hashes, and store the full returned string (it includes algorithm and salt).

## output-escaping: Escape output for its context
tags: php, xss, htmlspecialchars, escaping, templates, blade, twig, security
keywords: echo $_GET, raw html output
refs: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html

Echoing request data into HTML enables XSS. Use a template engine with auto-escaping (Blade `{{ }}`, Twig), or `htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')` for HTML. Blade `{!! !!}` disables escaping: use it only for trusted, sanitized HTML.

## laravel-eager-loading: Eager load Eloquent relations to avoid N+1 queries
tags: php, laravel, eloquent, n+1, eager loading, with, orm, performance
keywords: one query per row, lazy loading
refs: https://laravel.com/docs/11.x/eloquent-relationships#eager-loading

Accessing `$post->author` inside a loop issues one query per post. Load relations up front with `Post::with('author')->get()` (or `load()` on an existing collection), and call `Model::preventLazyLoading(! app()->isProduction())` so lazy loading throws in development.

## laravel-mass-assignment: Guard mass assignment with $fillable and validated input
tags: php, laravel, mass assignment, fillable, validation, form request, security
keywords: $request->all(), is_admin set by user
refs: https://laravel.com/docs/11.x/eloquent#mass-assignment

`User::create($request->all())` lets a client set any column, such as `is_admin`. Declare `$fillable` on models and pass only validated data: `User::create($request->validated())` from a Form Request with explicit rules.

## composer-autoload-and-lock: Commit composer.lock and rely on autoloading
tags: php, composer, dependencies, autoload, psr-4, lock file, security audit
keywords: require_once everywhere
refs: https://getcomposer.org/doc/01-basic-usage.md#commit-your-composer-lock-file-to-version-control

Commit `composer.lock` for applications so every environment installs identical versions, use PSR-4 autoloading instead of manual `require`, deploy with `composer install --no-dev --optimize-autoloader`, and run `composer audit` in CI.

## exceptions-not-warnings: Convert errors to exceptions and never suppress with @
tags: php, error handling, exceptions, error suppression, at operator, logging
keywords: @file_get_contents, warning ignored
refs: https://www.php.net/manual/en/language.operators.errorcontrol.php

The `@` operator hides failures and makes debugging impossible. Check return values (many built-ins return `false` on failure), throw domain exceptions, log in a single top-level handler, and never display errors to users in production (`display_errors=Off`, `log_errors=On`).
