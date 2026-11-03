# Status

Last updated 2026-11-03. See [docs/RELEASE_REPORT.md](docs/RELEASE_REPORT.md) for the audit,
implementation checklist, commands and validation record.

## Current state

SkillForge is an experimental local coding-guidance retriever. The Python 3.9+ pipeline,
rule-level BM25 retriever, project-stack detection, bounded rule delivery and multi-level
catalog are implemented. The optional hook remains off by default. The catalog exports 691
rules across 64 modules (including the core module): 515 rules are in 57 authored packs and
176 come from six imported upstream modules. All rules remain marked `untested`.

The expansion is a substantial curation draft, not a claim that hundreds of rules have been
independently reviewed. Authored packs cite HTTPS sources and record the documentation
version they were checked against; their generated provenance records `review: pending human
review`. The validator passes with two review notices for safe example code (`rm -rf` used
for trapped temporary-directory cleanup and PyTorch `model.eval()`).

## Measured results

Offline retrieval runs on the development set only (39 cases, seen during tuning):

| Measurement | Result |
|---|---:|
| Rule recall@4 | 51.3% |
| Precision@4 (macro over cases) | 25.0% |
| Pooled selected-rule precision | 26.1% (23 relevant / 65 unnecessary) |
| NDCG@4 | 0.472 |
| Prompts needing guidance with no selected rules | 5/39 |
| Dependency-complete briefs | 39/39 |
| Mean brief size | ~801 estimated tokens (characters / 4) |
| Mean local retrieval runtime | ~5 ms per development case |
| Ambiguous/follow-up set | 4/4 abstained |
| Mixed-technology set | 83.3% recall over 3 cases; 3/3 reached both labeled modules |

These labels and prompts have been inspected during implementation, and the precision is
still too low for a quality claim. The current scorecard does not measure code quality,
model output tokens, API requests, cached tokens, or cost. It is not a held-out evaluation.
No paid Claude comparison has been run, so no cost reduction is claimed.

The behavioral grader validates the Postgres queue task against 10 solution variants in
both static and embedded-Postgres modes: correct solutions pass 4/4 and each targeted broken
variant fails at least one relevant check. `react-waterfall` and `binary-search` are not yet
validated graders. No live Claude Code session or Windows/Linux installation was available
for this run.

## Release gaps

- Retrieval benchmark coverage is 39 core cases, 6 negatives, 4 ambiguous prompts and 3 mixed
  prompts; this is below the requested 100/50/30/30 sizes.
- There are three task fixtures, but only one behavioral grader has been validated. Security
  and performance task counts are below the requested targets.
- Most authored rules need independent human review. Automated checks establish structure,
  provenance fields, license allowlist status, source URL policy and basic injection/safety
  signals; they do not verify technical correctness or link freshness.
- No held-out routing set has been authored independently. No API cost, token-use or
  task-success comparison between native skills and SkillForge exists.
- CI currently runs on Linux; macOS and Windows installation behavior needs dedicated jobs.

## Repeat validation

```sh
npm test
npm run validate:library
npm run retrieval
npm run retrieval -- --cases benchmarks/retrieval-ambiguous.jsonl
npm run retrieval -- --cases benchmarks/retrieval-mixed.jsonl
npm run graders
```

The current implementation should be treated as a validated prototype and curation draft,
not a production-proven retrieval system.
