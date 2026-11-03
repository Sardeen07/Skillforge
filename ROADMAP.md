# Roadmap

Things that are designed or wanted but not built. Order is rough priority. The
experiment plan itself is in [STATUS.md](STATUS.md).

**Architecture work is paused** until the first real runs identify the next bottleneck.
Nothing below should start just because it is listed here.

## Retrieval

Build these only when a measured failure calls for them. Metadata and hand-declared
relations come first; embeddings and semantic dedupe come after.

- **Word forms.** "deep pages" misses a rule about "deeper pages" because the stemmer
  does not strip -er. A mixed-technology regression case fails on exactly this.
- **Task context beyond the prompt.** Use the files being edited and the active task,
  not just the raw prompt, so "the orders page is slow" can be resolved to a query,
  network or render problem instead of abstaining or guessing.
- **Version applicability.** The hook already records dependency versions (e.g.
  `react 19.0.0`); no rule declares a version requirement yet. Add per-rule version
  bounds when a rule is found to be wrong for some versions.
- **Hybrid retriever.** Keep BM25 as the zero-dependency default. Add an optional small
  local embedding model (SkillRet-style, ~0.6B) once the library passes a few hundred
  rules, combined with BM25 scores. Research on 690 skills found hybrid BM25 + dense
  retrieval at 73.5% hit@5, while an LLM-built graph added nothing. Measure it against
  this BM25 baseline, including latency and install cost.
- **Usage signal.** Log which delivered rules the agent actually applied (from
  transcripts) and feed that back as a prior. It was the only new signal that helped
  in the large-library retrieval study.
- **Catalog at scale.** At 132 rules the catalog is 9,341 characters, just under the
  hook cap. Past ~140 rules it needs to become two-level (module lines, then
  `--catalog <module>`), or be delivered as a skill description instead of a hook.

## Library

- **Scanner.** `forge/scan.py` (`npm run scan -- owner/repo ...` or `--seeds FILE`) clones
  each repo at one commit, finds every `SKILL.md`, and triages it: license (folder file,
  frontmatter, repo; most restrictive wins), prompt-injection and hidden-character checks,
  bundled scripts, size, and overlap with what is already imported. Verdicts are
  `accept`, `review`, `reject` or `known`; `--emit` writes the accepted ones as a curation
  file with `status: candidate`, which `sf.py import` understands and `export` leaves out
  of retrieval. Still missing: reading the Skills Directory ranking into seeds (the
  TypeScript stub in `forge/crawler/` only fetches it; `scan.py seeds-from-json` pulls
  `owner/repo` names out of its output, untested against the live API), turning a
  scanned skill into `rules/` files with `title`/`tags` (a thin SKILL.md is only
  split by headings), and a person reading every accepted skill before it is promoted.
- **Dedupe.** Detect overlapping rules across modules (e.g. two sources both teaching
  `Promise.all`), and keep one. Exact-duplicate suppression exists in the brief today;
  semantic dedupe does not.
- **Scoring.** Fill `score` in `index.json` from versioned task outcomes, never from
  development routing numbers. Promotion from `provisional` needs a native comparison.
- **More modes.** Only `coding` exists. `debugging`, `testing`, `writing` and
  `research` were once advertised; add them only with modules and tasks behind them.

## Measurement

- **Validate `react-waterfall`** with correct and broken solutions, and make its checks
  behavioral where possible. `pg-queue-throughput`'s keyset check is still static,
  because the agent may name its cursor function anything.
- **Combined delivery arm** (catalog plus brief), only if both do well separately.
- **Behavioral task suite** of 8-10 discriminating tasks (see STATUS next steps).
- **SQLite ingestion** of `ab.py` JSONL into the `runs` table, validating task,
  module and model versions and keeping errors and unknown costs. Until then JSONL is
  the record, and the database stays build-time only.
