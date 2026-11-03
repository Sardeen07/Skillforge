# Roadmap

The library and retrieval engine have expanded substantially, but release readiness is not
complete. See [STATUS.md](STATUS.md) and [docs/RELEASE_REPORT.md](docs/RELEASE_REPORT.md) for
measured results and verified limits.

## Priority 1: improve retrieval quality

- Review false positives in the 691-rule catalog; the current 39-case development set
  shows useful recall but low precision and is not independent of tuning.
- Add independent held-out retrieval cases before further threshold changes.
- Expand tests to multi-stack manifests and ambiguous multi-technology prompts.
- Measure NDCG, precision, recall, token estimates and latency on the same frozen cases.
- Keep deterministic local BM25 as default; evaluate optional semantic retrieval only against
  the recorded baseline.

## Priority 2: curate and verify the library

- Complete independent human review of authored rule packs; keep evidence `untested` until
  behavioral or controlled evaluation supports a stronger status.
- Link-check references and record exact documentation versions per authored rule.
- Add cross-module near-duplicate detection and a source/license review checklist to PR CI.
- Continue expanding the benchmark task suite with behavioral graders, especially for
  security and performance tasks.

## Priority 3: product validation

- Run frozen, repeated Claude comparisons for no-skill, native, skill-only, hook, catalog and
  expert-selected arms. Record actual input/output/cache tokens, cost, requests, latency and
  behavioral task outcomes. Credentials and a live Claude Code environment are required.
- Add at least 100 retrieval cases, 50 negative cases, 30 ambiguous cases, 30 mixed-stack
  cases, 20 security tasks and 20 performance tasks.
- Validate installation and hook behavior on Windows and Linux in CI in addition to macOS.
- Review documentation after results change; publish only reproducible measurements.
