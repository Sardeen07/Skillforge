# Architecture

```
curation (forge/curation/coding.json, authored RULES.md packs, pinned upstream commits)
   │  forge/sf.py import / export          forge/validate_library.py
   ▼
plugin/library/index.json + modules/ + technologies.json (+ optional synonyms.json)
   │  read-only at runtime, no network, no database
   ▼
retrieval.py  ── load_rules → Index (BM25) → rank (per sentence) → interleave
   │
delivery.py   ── build_brief (budget, dependencies, conflicts, session) | catalog_text | get_rules
   │
compose.py (CLI / skill)        hook.py (UserPromptSubmit, SessionStart; off by default)
```

## Library

- **Rule layouts.** (1) A reference file with `title`/`tags` frontmatter under `rules/` or
  `references/` of an imported module. (2) A section of a procedural guide (split at `##`
  headings; later steps declare `requires` on earlier ones). (3) An entry of an authored
  pack, `RULES.md`: `## id: Title`, then `tags:`, `keywords:`, `refs:`, optional
  `technologies:`, `requires:`, `conflicts:`, `versions:`, `evidence:` lines, then the body.
  A malformed pack (duplicate id, no tags, empty body) fails the load.
- **Provenance.** Each module folder has `SOURCE.json`: repository, exact commit and license
  for imports; `kind: authored`, the documentation version checked against, authorship and
  review state for packs. `sf.py export` writes a reproducible `index.json` (content digest,
  no timestamp).
- **Taxonomy.** `technologies.json` maps 53 technologies to strong aliases (naming the
  technology), weak hints (a small boost only), implications (Next.js → React, Postgres →
  SQL), package names per ecosystem and marker files. Ambiguous words (`go`, `c`, `express`,
  `node`, `rails`, `cargo`, `next`) only count inside unambiguous phrases.

## Retrieval (per prompt, ~3 ms after load)

1. Split the prompt into sentences and lines; each is ranked on its own.
2. BM25 over title/tags/keywords (counted twice) and body. Comparative word forms are tried
   at half weight if the library contains them; curated synonyms are opt-in.
3. **Evidence floor:** raw score ≥ `MIN_SCORE` (12) and at least `MIN_MATCHED` (2) distinct
   prompt words in the rule. Priors never lift a rule over the floor.
4. **Technology prior:** a named technology ×2 for its rules and ×0.05 for other
   technologies' rules; hints ×1.3; detected stack ×1.2 on-stack / ×0.5 off-stack.
   Technology-agnostic rules are never demoted.
5. **Ambiguity:** with no technology named, if two unrelated technologies' best rules score
   within 80% of each other, only technology-agnostic rules are kept.
6. **Coverage:** a sentence naming several technologies gives each its best qualifying rule
   first (floor 0.6 × MIN_SCORE, own technology counting as a matched word); each clause of a
   multi-concern sentence gets its best rule at 0.75 × MIN_SCORE.
7. Keep rules within `RELATIVE` (0.75) of the sentence's best, at most 4 per sentence (up to
   7 when coverage needs more); interleave sentences round-robin; drop hits under
   `BRIEF_RELATIVE` (0.55) of the prompt's best, except technology coverage picks.

Every constant is overridable by environment variable for experiments and was chosen with
`forge/sweep_retrieval.py` on development sets only ([BENCHMARKS.md](BENCHMARKS.md)).

## Delivery

- **Brief:** the coding core, then each selected rule with every rule it `requires`
  (dependencies first) or not at all; a rule conflicting with one already delivered is
  refused. The whole serialized brief must fit the budget (characters / 4). Rule text is
  delivered in compact form: imported files lose their frontmatter and a heading repeating
  the title; wording is otherwise unchanged. Each rule carries a one-line attribution
  (`repo@commit (license) · evidence`).
- **Session:** content-addressed keys (path + sha256) so a rule is not re-sent in the same
  conversation; compaction or resume marks earlier rules as possibly lost, and a content-free
  follow-up restores the last active rules once.
- **Catalog:** full (one line per rule) when it fits the budget, otherwise two-level: one line
  per module, plus the rule lists of modules on the detected stack while they fit;
  `--catalog <module>` lists the rest.
- **Caching:** loaded rules and the BM25 index are cached per process, keyed by a fingerprint
  of `index.json` and every rule file's size and mtime, so an edited file is never served stale.

## Safety

- Runtime only reads files inside `plugin/library` (paths are resolved and checked), never
  executes library content, and parses manifests with size caps.
- The hook exits 0 on every error and logs instead; invalid configuration falls back to defaults.
- `validate_library.py` and `scan.py` reject prompt-injection phrases, hidden Unicode,
  credential paths, pipe-to-shell commands and non-allowlisted licenses before rules enter
  the library; authored references must be HTTPS on a reviewed host list.

## Scaling

A 691-rule library loads in ~25 ms and ranks in ~3 ms. Loading is linear in rule count and
ranking walks postings lists, so 2,000 rules are expected to stay well under the hook
timeout; the two-level catalog keeps catalog mode bounded at any size. Not yet measured at
2,000 rules.
