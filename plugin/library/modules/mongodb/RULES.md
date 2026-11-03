---
module: mongodb
capability: MongoDB data modeling, indexing and safety
technologies: mongodb
applies: mongodb, mongo, mongoose, document, aggregation, index
checked_against: MongoDB 8.0 manual
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## model-for-access-patterns: Model documents around how the data is read
tags: mongodb, data modeling, embedding, referencing, schema design, document size
keywords: joins with lookup everywhere, 16MB limit
refs: https://www.mongodb.com/docs/manual/data-modeling/

Embed data that is read together and bounded in size (an order's line items); reference data that is shared, large or unbounded (a user's activity log). Avoid arrays that grow without limit: documents are capped at 16 MB and large documents are rewritten on each update.

## esr-index-rule: Build compound indexes in Equality, Sort, Range order
tags: mongodb, compound index, esr rule, explain, collection scan, query performance
keywords: COLLSCAN, in-memory sort
refs: https://www.mongodb.com/docs/manual/tutorial/equality-sort-range-guideline/

Order compound index fields: equality-matched fields first, then sort fields, then range filters. Confirm with `explain("executionStats")` that the plan is `IXSCAN`, without in-memory `SORT`, and that `totalDocsExamined` is close to `nReturned`.

## nosql-injection: Prevent operator injection from request data
tags: mongodb, nosql injection, security, query operators, sanitize, mongoose, input validation
keywords: {$ne: null} login bypass
refs: https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html

If a request field can be an object, `{ password: req.body.password }` becomes `{ password: { $ne: null } }` and matches anything. Validate types with a schema (strings must be strings), reject keys starting with `$` or containing `.`, enable Mongoose `sanitizeFilter`, and never pass user input to `$where` or `$function`.

## write-concern-durability: Use majority write concern for data you cannot lose
tags: mongodb, write concern, durability, replica set, read concern, transactions
keywords: acknowledged write lost on failover
refs: https://www.mongodb.com/docs/manual/reference/write-concern/

With `w: 1`, a write acknowledged by the primary can be rolled back if it fails over before replication. Use `w: "majority"` (the default since 5.0 for most deployments) for important writes, and `readConcern: "majority"` for reads that must not see rolled-back data.

## atomic-update-operators: Update with atomic operators, not read-modify-write
tags: mongodb, atomic updates, $inc, $set, findOneAndUpdate, race condition, concurrency
keywords: lost update counter
refs: https://www.mongodb.com/docs/manual/core/write-operations-atomicity/

Reading a document, changing it in application code and saving it back loses concurrent updates. Use single-document atomic operators (`$inc`, `$set`, `$push`, `$addToSet`) with conditions in the filter (`{ _id, stock: { $gte: 1 } }`), or `findOneAndUpdate`. Use multi-document transactions only when invariants span documents.

## aggregation-early-filter: Filter and project early in aggregation pipelines
tags: mongodb, aggregation pipeline, $match, $project, $lookup, performance, memory limit
keywords: aggregation slow, exceeded memory limit
refs: https://www.mongodb.com/docs/manual/core/aggregation-pipeline-optimization/

Put `$match` (index-backed) and `$project` as early as possible so later stages process fewer and smaller documents, index the foreign field of `$lookup`, and add `allowDiskUse` only after reducing data, not as a fix for unbounded pipelines.

## schema-validation-mongo: Enforce a schema with JSON Schema validation
tags: mongodb, schema validation, json schema, data quality, mongoose schema
keywords: inconsistent document shapes
refs: https://www.mongodb.com/docs/manual/core/schema-validation/

Flexible schemas still need rules. Add `$jsonSchema` validators to collections for required fields and types so every client (not only the one using Mongoose) writes valid documents, and version document shapes with a `schemaVersion` field during migrations.

## pagination-mongo: Paginate with range queries on an indexed field, not skip
tags: mongodb, pagination, skip, limit, range query, cursor, performance
keywords: skip large slow
refs: https://www.mongodb.com/docs/manual/reference/method/cursor.skip/

`skip(n)` walks n index entries or documents, so deep pages are slow. Page by the last seen sort key: `find({ _id: { $gt: lastId } }).sort({ _id: 1 }).limit(50)`, using a compound key with `_id` as tiebreaker when sorting by a non-unique field.
