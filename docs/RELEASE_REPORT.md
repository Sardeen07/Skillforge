# Release report: v0.2.0 (2026-11-05)

Covers two passes: 2026-11-03 (library expansion, taxonomy, validator; audit in
[AUDIT.md](AUDIT.md)) and 2026-11-05 (benchmark suite, retrieval tuning, behavioral tasks,
cost tooling, cross-platform CI, docs). Measurements: [BENCHMARKS.md](BENCHMARKS.md).

## Completed

**Library**
- 691 rules (from 132) in 63 modules plus the core: 515 authored rules in 57 `RULES.md`
  packs and 176 rules from pinned MIT upstream modules (react-native and
  react-composition added at vercel-labs/agent-skills@1a2c79d). Every rule has an ID, title,
  tags, technologies (module or rule level), keywords, references, provenance, license,
  pinned commit or checked-against documentation version, evidence status (`untested`) and
  optional requires/conflicts/versions.
- `technologies.json`: 53 technologies with strong aliases, weak hints, implications,
  package names and marker files. `synonyms.json`: curated expansion vocabulary (opt-in).
- `forge/validate_library.py`: schema, provenance, license allowlist, HTTPS references on a
  reviewed host list (optional link check), exact-duplicate detection, relation integrity,
  injection and hidden-character scan.

**Retrieval and delivery**
- Taxonomy-driven technology priors; manifest detection for npm, Python, Go, Rust, Maven/
  Gradle, Ruby, PHP, Dart, Docker, Terraform, Kubernetes and GitHub Actions projects.
- Coordination guard, named-technology and clause coverage, ambiguity guard with
  technology-agnostic fallback, brief-level relative cut; parameters swept on dev sets.
- Compact rule formatting, one-line attribution, in-process caching keyed by file
  fingerprints, two-level catalog that fits the hook budget at any library size.
- Hook: Python 3.9+, invalid budget falls back to the default, catalog mode works at scale,
  every error exits 0.

**Benchmarks**
- Routing: 109 dev, 30 mixed, 20 security, 20 performance, 28 task-prompt, 50 negative,
  30 ambiguous cases; 74 held-out cases frozen by hash before tuning. Recall@K, precision,
  NDCG@K, abstention, unnecessary tokens, latency (mean and p95); label validation.
- 30 behavioral tasks (27 new: 9 security, 9 performance, 9 correctness/concurrency/
  resilience) with hidden graders; 29 validated against 81 reference and broken variants.
- `forge/context_cost.py`: offline guidance-token comparison across the six arms.
- `forge/sweep_retrieval.py`: reproducible parameter sweeps (dev sets only).

**Fixes found along the way**
- A/B `native` arm installed authored packs without skill frontmatter, so 57 of 63 modules
  would not have registered as native skills: the comparison would have been unfair.
- A dev label (`systematic-debugging#*`) matched no rule, so that case could never score.
- `binary-search`'s grader printed no `SCORE` line, so the A/B runner could not score it.
- Canonical technology names (`go`, `c`) and words such as `express`, `node`, `rails`,
  `cargo` counted as naming a technology.
- Go module dependencies with a major-version suffix (`.../v5`) were not detected.
- The brief-level cut removed the weaker technology's coverage pick in mixed prompts.
- The ambiguity guard discarded relevant technology-agnostic rules.
- An empty `technologies:` frontmatter line swallowed the next line (2026-11-03).
- The password-hashing reference used `hashlib.scrypt`, which macOS's LibreSSL-based system
  Python lacks; it now uses PBKDF2-HMAC-SHA256 (600,000 iterations), available everywhere.

## Validation record (2026-11-05, macOS, Python 3.12 venv and system Python 3.9.6)

| Check | Result |
|---|---|
| `npm test` (Python 3.12) | 161 tests, all passing |
| `npm test` (macOS system Python 3.9.6, no dev dependencies) | 161 tests, all passing |
| `npm run validate:library` | 691 rules, 64 modules, 505 references; 0 errors, 2 reviewed notices (`rm -rf` in a trap cleanup example, `model.eval()`) |
| `npm run graders` | 29 tasks, 81 variants, all as expected (pg task in both static and embedded-Postgres modes); `react-waterfall` not validated |
| `npm run retrieval:suite` / `retrieval:heldout` | see [BENCHMARKS.md](BENCHMARKS.md) §1 |
| `npm run cost` | see [BENCHMARKS.md](BENCHMARKS.md) §2 |
| A/B dry run (`none,native,sf-hook,sf-catalog` on `ssrf-url-check`) | isolated configs built for every arm |
| Hook end to end through `sh plugin/hooks/run-hook.sh` | ~0.2 s per prompt; garbage input exits 0 |
| CI matrix (Linux, macOS, Windows × Python 3.9, 3.12) | defined in `.github/workflows/ci.yml`; not yet run (no push from this environment) |

## Remaining limitations

- **No paid model comparison.** Token usage, cached tokens, request counts, cost and task
  outcomes per arm are unknown; no cost or quality improvement is claimed.
- Authored rules are machine-drafted with cited references and automated checks, but
  **not human-reviewed**; all evidence is `untested`.
- Routing on real task prompts is weak (55% recall, 21% precision). The held-out set shares
  its author with the rules and overstates real performance; no independent set exists.
- Whether the new tasks discriminate between arms is not measured.
- Optional semantic retrieval was not built; synonyms measured net-negative and are off.
- Live Claude Code sessions on Windows and Linux were not available here.
- The repository is committed locally; nothing has been pushed.

## Release checklist

- [x] Unit and integration tests pass (Python 3.12 and 3.9)
- [x] Library validation: 0 errors
- [x] Grader validation for 29 of 30 tasks
- [x] Retrieval benchmarks on dev, mixed, security, performance, task, negative, ambiguous sets
- [x] Held-out set frozen before tuning and scored once per retriever version
- [x] Offline context-cost comparison
- [x] Docs (README, STATUS, ROADMAP, ARCHITECTURE, BENCHMARKS, CONTRIBUTING_LIBRARY, TROUBLESHOOTING) match the implementation
- [x] Working tree committed in logical commits
- [ ] CI run on all three operating systems (needs a push)
- [ ] Paid, frozen, repeated A/B comparison
- [ ] Human review of authored packs; independent held-out set
