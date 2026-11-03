# Audit (2026-11-03)

An audit of the repository at `6429fde` before the v1 release work. Every finding
below was checked against the code or by running it; numbers are from this machine
(macOS, Python 3.12 venv, Node 20).

## What works and is kept

- **Pipeline.** Curation JSON -> `sf.py import` (pinned commits, SQLite record) ->
  `sf.py export` -> `plugin/library/index.json`. Sound; extended, not replaced.
- **Rule-level BM25 retrieval** with technology priors, abstention, an ambiguity guard,
  per-sentence ranking and dependency closure. Sound core; extended.
- **Bounded delivery** with session de-duplication, dependency-or-nothing groups and
  conflict refusal. Kept.
- **A/B runner** (`ab.py`): isolated arms, frozen conditions, usage capture from
  `claude -p --output-format json`, saved artifacts. Kept.
- **Grader v2** for `pg-queue-throughput` (behavioral, validated with 10 variants). Kept.
- **Scanner** (`scan.py`): license, injection, hidden characters, scripts, overlap. Kept
  and reused by the new library validator.
- Baseline: 121 tests pass; dev rule recall@4 58.1%, precision 42.2%.

## Findings

| # | Severity | Finding | Evidence |
|---|---|---|---|
| 1 | High | The launcher and hook demand Python 3.10, but the code runs on 3.9. Stock macOS ships 3.9 as `python3`, so on a default Mac the plugin silently does nothing. | `node forge/py.mjs` -> "no Python 3.10+ found"; `/usr/bin/python3 compose.py ...` (3.9.6) works. |
| 2 | High | Catalog mode cannot scale: past ~140 rules the catalog exceeds the hook cap, and the hook then **silently skips it**. With a larger library catalog mode delivers nothing. | `hook.py`: `if ... len(text) > budget * 4: ... "catalog skipped"`. |
| 3 | High | Technology awareness is limited to React/Next.js and Postgres: the taxonomy is per-module `technologies` lists and stack detection knows ~12 package names. Multi-technology prompts outside those two cannot be routed. | `retrieval.PACKAGES`, `technologies()`. |
| 4 | Medium | Every prompt re-reads and re-tokenizes every rule file. Cost grows linearly with the library; `field_hits` is a linear scan per rule (quadratic when enabled). | `load_rules`, `Index.__init__`, `Index.field_hits`. |
| 5 | Medium | Delivered text includes each rule's YAML frontmatter and a heading that repeats the title, so every rule pays for its title two or three times. | `delivery.build_brief` uses `rule['text']`. |
| 6 | Medium | No library validation: missing titles/tags, unknown technologies, missing license or commit, injection text or duplicates in a rule are not caught at build time. Only relation names are checked (at runtime). | No validator exists. |
| 7 | Medium | Multi-technology sentences: only technologies with their own module get a guaranteed slot, and at most `PER_PART = 4` rules per sentence, so a sentence naming four technologies cannot cover them. | `rank()`. |
| 8 | Medium | No query expansion beyond comparative word forms; no aliases (`k8s`, `postgresql`, `pg`, `tf`). "PostgreSQL" does not match the `postgres` technology. | `terms()`, `Index.expand()`. |
| 9 | Medium | The benchmark is 52 retrieval cases, all seen while tuning; no held-out set; metrics stop at recall/precision (no NDCG, MRR, latency, unnecessary tokens). | `benchmarks/*.jsonl`, `score_retrieval.py`. |
| 10 | Medium | Only one validated behavioral coding task. | `benchmarks/tasks/README.md`. |
| 11 | Low | `SKILL.md` description advertises only debugging/testing/React/Postgres; Claude will not call the skill for other stacks. | `plugin/skills/skillforge/SKILL.md`. |
| 12 | Low | A malformed `SKILLFORGE_HOOK_BUDGET` raises inside the hook; it is caught and logged, but the brief is lost instead of falling back to the default. | `hook.handle`. |
| 13 | Low | `index.json` carries `generated_at`, so every export changes the file even when nothing else did (non-reproducible builds). | `sf.export`. |
| 14 | Low | Plugin manifest description says rules are delivered "on every prompt", but the hook is off by default. | `plugin.json`, `marketplace.json`. |
| 15 | Low | `/forge-status` and `SKILL.md` hardcode `python3`, contradicting the repo's own Windows guidance. | `plugin/commands/forge-status.md`. |

## Prioritized checklist

1. Python 3.9+ support in the launcher and hook (finding 1).
2. Technology taxonomy with aliases, implications and manifest detection for every
   target ecosystem (3, 8).
3. Library validator: schema, provenance, license, injection, duplicates, relations (6).
4. Library expansion to 500+ rules: import the remaining permissively licensed upstream
   rule sets at pinned commits; author the rest with cited authoritative references,
   rendered from reviewable packs; `evidence: untested` throughout.
5. Retrieval: compiled index with integrity check (4), synonyms (8), field-weighted
   BM25, multi-technology coverage (7), concern detection, conflict handling.
6. Delivery: compact formatting (5), two-level catalog (2), budget enforcement tests.
7. Benchmarks: >=100 dev, 50 negative, 30 ambiguous, 30 mixed, 20 security, 20
   performance retrieval cases, a held-out set written before tuning, NDCG/MRR/latency/
   token metrics, 30 behavioral coding tasks with validated graders, offline context-cost
   comparison per arm.
8. Hardening: hook fallbacks (12), reproducible export (13), docs and manifests (11, 14, 15).
9. Tests for each of the above; docs updated to measured results.
