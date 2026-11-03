---
module: django
capability: Django ORM performance, security and migrations
technologies: django
applies: django, orm, queryset, migrations, drf, admin
checked_against: Django 5.1 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## select-prefetch-related: Use select_related and prefetch_related to avoid N+1 queries
tags: django, orm, n+1, select_related, prefetch_related, queryset, performance
keywords: query per row in template, django debug toolbar
refs: https://docs.djangoproject.com/en/5.1/ref/models/querysets/#select-related

Accessing `order.customer` or `order.items.all()` in a loop runs a query per row. Use `select_related('customer')` for foreign keys (a join) and `prefetch_related('items')` for many-to-many and reverse relations (one extra query). In DRF apply them in `get_queryset`. Verify with Debug Toolbar or `assertNumQueries`.

## queryset-evaluation: Let the database filter, count and check existence
tags: django, orm, queryset, exists, count, values, only, bulk_create
keywords: len(queryset), save in a loop
refs: https://docs.djangoproject.com/en/5.1/topics/db/optimization/

Use `.exists()` instead of `if qs:`, `.count()` instead of `len(qs)`, `.values_list()`/`.only()` to fetch fewer columns, `.iterator()` for large scans, and `bulk_create`/`bulk_update`/`update()` instead of saving in a loop. `F()` expressions update counters atomically.

## atomic-transactions: Wrap multi-step writes in transaction.atomic and use on_commit
tags: django, transaction, atomic, on_commit, celery, consistency, select_for_update
keywords: task runs before commit, partial save
refs: https://docs.djangoproject.com/en/5.1/topics/db/transactions/

Group related writes in `with transaction.atomic():`. Enqueue tasks or send emails with `transaction.on_commit(lambda: task.delay(obj.id))` so they never run for rolled-back data. Use `select_for_update()` inside the transaction for read-modify-write on contended rows.

## safe-migrations: Write migrations that are safe on large tables
tags: django, migrations, schema change, zero downtime, add column, index, large table
keywords: migration locked table, deploy downtime
refs: https://docs.djangoproject.com/en/5.1/topics/migrations/

Adding a non-null column or a regular index can lock big tables. Add nullable columns first, backfill in batches, then add constraints; on Postgres use `AddIndexConcurrently` in a non-atomic migration. Separate schema and data migrations, and keep code compatible with old and new schema during a rolling deploy.

## secure-settings: Keep production settings secure
tags: django, security, settings, debug, secret key, allowed hosts, csrf, deployment
keywords: DEBUG = True in production
refs: https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

Run `python manage.py check --deploy`. In production: `DEBUG = False`, `SECRET_KEY` from the environment, explicit `ALLOWED_HOSTS`, `SECURE_SSL_REDIRECT`, secure session and CSRF cookies, HSTS, and never disable CSRF middleware for convenience.

## orm-raw-sql-safety: Never format user input into raw() or extra()
tags: django, sql injection, raw sql, extra, cursor, security, parameters
keywords: raw(f"..."), RawSQL
refs: https://docs.djangoproject.com/en/5.1/topics/db/sql/

The ORM parameterizes for you; raw SQL does not if you format strings. Use `Model.objects.raw("... WHERE id = %s", [user_id])` and `cursor.execute(sql, params)`; never f-strings or `%` formatting on the SQL itself. Avoid `.extra()`.

## drf-permissions-and-scoping: Scope querysets to the user and set default permissions in DRF
tags: django, drf, django rest framework, permissions, authorization, idor, queryset
keywords: user can see other users objects
refs: https://www.django-rest-framework.org/api-guide/permissions/

Set `DEFAULT_PERMISSION_CLASSES` to require authentication, and filter `get_queryset()` by the requesting user or tenant so lookups cannot reach other users' rows (IDOR). Use explicit serializer `fields`, never `__all__` on models with sensitive columns.

## indexes-and-constraints-django: Declare indexes and constraints in Meta
tags: django, models, indexes, unique constraint, check constraint, database integrity
keywords: duplicates despite validation
refs: https://docs.djangoproject.com/en/5.1/ref/models/constraints/

Declare `Meta.indexes` for hot filter and order columns and `Meta.constraints` (`UniqueConstraint`, `CheckConstraint`) for invariants, so the database enforces them under concurrency. Model `clean()` is not run by `save()` or bulk operations.
