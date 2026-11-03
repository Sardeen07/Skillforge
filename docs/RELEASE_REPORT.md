# Engineering report — 2026-11-03

## Audit and prioritized implementation checklist

The pre-change audit is recorded in [AUDIT.md](AUDIT.md). Priority was given to the runtime
and library growth paths:

1. Support Python 3.9 in the launcher and hook; confirm the existing tests still run there.
2. Add a taxonomy for technologies, aliases, implications and manifest detection.
3. Keep BM25 local and dependency-free; add reusable cached retrieval context and query
   expansion already supported by the library format.
4. Expand the rule catalog with attributed upstream and authored sources, without changing
   their evidence status from `untested`.
5. Keep delivery budgets strict and make catalog browsing work beyond the hook size limit.
6. Add schema, source, license, safety and duplicate validation and benchmark quality signals.
7. Update docs to report measured behavior and outstanding work without claiming cost gains.

## Completed in this pass

- Expanded the exported library from 132 to 691 rules in 64 modules (63 guidance modules
  plus the core). It contains 515 authored rules in 57 reviewable `RULES.md` packs and 176
  rules from six pinned upstream modules.
- Added `technologies.json` with technology aliases, weak hints, implications, package
  names and manifest markers. The retriever still abstains when textual evidence is weak.
- Added authored-pack parsing, rule-level curation keywords, SHA library digest generation,
  deterministic exports, in-process rule/index caching, compact delivery, and bounded
  two-level catalogs. `compose.py --catalog <module>` lists that module's rules.
- Added `forge/validate_library.py` and `npm run validate:library`. It checks exported
  eligibility against curation, source/license provenance, rule structure and metadata,
  HTTPS references against the reviewed host registry, exact duplicate bodies, relation
  integrity and scanner safety flags. Optional `--verify-links` checks URLs over the network.
- Added NDCG@K, precision@K and local runtime fields to the offline retrieval scorecard.
- Lowered the runtime requirement to Python 3.9, and broadened plugin skill discovery
  wording to reflect the catalog.
- Updated regression expectations for new modules where Next.js or generic SQL guidance is
  relevant, and added validator and NDCG tests.

## Validation record

- Final full suite: 123 tests passed on Python 3.12 (121 existing plus 2 new validator/metric tests). The launcher compatibility change was exercised on the host's Python 3.9.
- Library validation: **691 rules, 64 modules, 505 unique source references; 0 errors, 2 reviewed safety notices and 7 URL-check warnings**. The optional `--verify-links` check ran; 7 MySQL documentation references returned 403 (the host denied automated HEAD requests); the other references returned successfully.
- Development retrieval: rule recall@4 **51.3%**, macro precision@4 **25.0%**, pooled
  precision **26.1%**, NDCG@4 **0.472**, and mean local runtime **~5 ms**. Mean brief size
  was about **801 estimated tokens**. Dataset size: 39 core development cases.
- Ambiguous/follow-up set: **4/4 abstained**. Mixed set: **83.3% recall across 3 cases**.
- Behavioral grader validation: Postgres queue task, 10 variants in static and embedded
  Postgres modes; correct variants score 4/4 and every targeted broken variant fails a
  relevant check. Two other task graders remain unvalidated.
- Full model/API comparison: **not run**. Input/output/cache tokens, request counts, price,
  and task-success deltas across native skills and SkillForge are unknown. No savings claim
  is justified.

## Known limitations

The expanded rule set is not independently reviewed and every rule remains `untested`.
The routing development data is small, was used during tuning, and reports low precision.
There is no independent held-out evaluation, only 39 main retrieval cases, 6 negative, 4
ambiguous and 3 mixed cases, three coding task fixtures, and only one validated behavioral
grader. Link freshness and cross-platform install behavior are not established. The requested
benchmark sizes (100 retrieval, 50 negative, 30 ambiguous, 30 multi-technology, 20 security
and 20 performance tasks) are not met. There is no evidence yet that SkillForge improves
behavior or lowers actual API cost.

## Release checklist

- [x] Python 3.9+ launcher/hook path exercised locally
- [x] Final unit/integration suite: 123 passed
- [x] Library metadata/license/safety validation command
- [x] Rule context budget and catalog size enforcement tests
- [x] Behavioral grader run for the Postgres queue fixture
- [x] Run the final full suite including newly added validator/metric tests
- [ ] Independently review authored packs and verify every source link
- [ ] Reach the requested benchmark suite sizes and prepare held-out cases independently
- [ ] Run repeated, controlled model comparisons and report actual token/cost/task outcomes
- [ ] Validate install and hook behavior on Windows, Linux and macOS
- [ ] Commit the finished release changes
