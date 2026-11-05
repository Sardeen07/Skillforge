# Roadmap

Designed or wanted, not built. Measured state is in [STATUS.md](STATUS.md).

## Priority 1: evidence

- **Paid A/B comparison** (`forge/ab.py`) of none / native / skillforge / sf-hook /
  sf-catalog / sf-expert on a frozen task suite with repeats: input, output and cached
  tokens, requests, cost, latency and per-check grader outcomes. Requires a model choice and
  API budget. Only after this may any rule's evidence change from `untested`.
- **Expert lists** (`benchmarks/expert/<task>.json`) for the new tasks, each reviewed by a
  second developer before `sf-expert` runs.
- **Discrimination check:** run the `none` arm on every task; drop or harden tasks every
  arm solves.
- **SQLite ingestion** of A/B JSONL into the `runs` table.

## Priority 2: retrieval on real prompts

- Routing on the 28 task prompts is 55% recall / 21% precision. Candidates, each to be
  measured on `tasks` and dev sets before adoption: identifier-aware tokenization
  (`render_report` → render, report; `readFileSync` → read file sync), per-rule symptom
  vocabulary in `keywords`, sentence weighting that discounts filler sentences.
- **Optional semantic scorer** (small local embedding model, BM25 + dense fusion) behind a
  flag, benchmarked on the same sets including latency and install size. Off by default
  unless it wins.
- **Version applicability:** the `versions:` field is parsed but not yet used to filter
  rules against detected dependency versions.
- **Usage signal:** learn from transcripts which delivered rules were applied.

## Priority 3: library

- Human technical review of all 57 authored packs; record reviewer and date.
- Semantic near-duplicate detection across modules (exact duplicates are already rejected).
- Re-pin upstream modules periodically and diff rule text before accepting updates.
- Grow toward 1,000-2,000 rules where review capacity allows; architecture is linear in
  rule count (measure load and ranking time at 2,000).

## Priority 4: platform

- Validate `react-waterfall`'s grader (needs Node and TypeScript in CI).
- Confirm hook behavior inside live Claude Code sessions on macOS, Linux and Windows
  (CI exercises the hook through `sh` on all three, but not inside Claude Code).
- Combined delivery arm (catalog plus brief), only if both do well on their own.
