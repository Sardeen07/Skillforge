# SkillForge

SkillForge picks the few curated coding rules that fit a task and hands them to Claude
within a fixed size budget.

**Hypothesis, not a result:** handing over a small, well-chosen set of rules gets better
code per dollar than native skill loading, at least once a library is large enough for
native selection to struggle. Nothing here shows that yet. Published results point
both ways: some benchmarks report large average gains from curated skills, while
others report little gain on software-engineering tasks, with most skills changing
nothing. So *which* guidance is curated may matter as much as how it is retrieved.
See [STATUS.md](STATUS.md).

> Status: working pipeline, **not yet benchmarked against native skills**. Every rule's
> evidence status is `untested` until measured runs show it helps.

## How it works

- **Rules are the unit.** A rule is one curated reference file (e.g.
  `postgres/lock-skip-locked`) or one section of a procedural guide (e.g.
  `systematic-debugging/phase-1-root-cause-investigation`). The library has 132.
- **Each rule carries metadata**, declared by hand in `forge/curation/coding.json`:
  applicability (technologies), `requires` (steps that must come with it), `conflicts`,
  provenance (pinned source and license) and evidence status. A later step of a
  procedure is delivered together with the steps before it, or not at all.
- **Retrieval** (`retrieval.py`) is BM25 over each rule's title, tags and text. A
  technology named in the prompt, or found in the project's manifests, reorders and
  demotes rules. It never selects a rule on its own. When the evidence is weak, or split
  between technologies, nothing is delivered.
- **Delivery is the open question**, so it is a switch, not a decision
  (`SKILLFORGE_HOOK`):

  | Variant | What enters context | Default |
  |---|---|---|
  | `off` | Only the SkillForge skill; Claude decides when to call it | yes |
  | `brief` | A hook injects the selected rules on each prompt that matches | |
  | `catalog` | A hook injects a one-line-per-rule catalog once; Claude fetches rules by ID | |
  | `fixed` | A hook injects a fixed rule list (the expert-selection experiment arm) | |

  Catalog plus brief together is not built; it is worth building only if both do well
  on their own. Injection only puts text in context. It does not show that the model
  used it.
- **Bounded.** A hook brief is capped at `SKILLFORGE_HOOK_BUDGET` estimated tokens
  (default 2,400, about 9,600 characters). A reported Claude Code behavior cuts hook
  output above 10,000 characters to a preview. That has not been reproduced here, so
  the cap is a conservative setting, not a verified limit.

## Install (Claude Code)
```
/plugin marketplace add Sardeen07/Skillforge
/plugin install skillforge@skillforge
```
Requires Python 3.10+ on the PATH (`python3`, `python` or `py`). The hook is off
unless you set `SKILLFORGE_HOOK`. With it on and no usable Python, it does nothing
rather than blocking your prompt.

## Try it

```sh
py=forge/py.mjs      # picks a working python3 or python for you
node $py plugin/skills/skillforge/scripts/compose.py "Our Postgres workers wait on each other. Deep report pages are slow."
node $py plugin/skills/skillforge/scripts/compose.py --catalog
node $py plugin/skills/skillforge/scripts/compose.py --rule postgres/data-pagination
node $py plugin/skills/skillforge/scripts/compose.py --status      # what the last brief delivered, and why
```

## Measure it

```sh
python -m pip install -r requirements-dev.txt        # embedded Postgres for the behavioral grader (use a .venv)
npm test                                              # 89 unit, hook, session, runner and grader tests
npm run graders                                       # do graders pass correct solutions and fail broken ones?
npm run retrieval                                     # rule recall@4, precision, dependency completeness
npm run retrieval -- --baseline                       # the old keyword module selector, for comparison
npm run retrieval -- --cases benchmarks/retrieval-negatives.jsonl --stack react,postgres
npm run retrieval -- --cases benchmarks/retrieval-ambiguous.jsonl   # vague prompts and follow-ups
npm run retrieval -- --cases benchmarks/retrieval-mixed.jsonl       # prompts naming two technologies
npm run ab -- --dry-run --arms none,native,sf-hook,sf-catalog,sf-expert
```

The routing scorecard scores the rules the brief actually delivers, not the module
chosen. It classifies every delivered rule as relevant, unnecessary, or supporting (a
declared dependency), and counts prompts that got no guidance, because recall alone
rises just by delivering more and precision alone rises by staying silent. Current development numbers are in [STATUS.md](STATUS.md); they come from cases
seen while tuning, so they are optimistic until a held-out set is scored
([benchmarks/heldout/](benchmarks/heldout/README.md)).

`forge/ab.py` runs real Claude Code sessions in isolated throwaway projects. Arms:
`none`, `native` (the same modules as ordinary skills), `skillforge` (skill only),
`sf-modules` (delivery ablation), `sf-hook`, `sf-catalog`, and `sf-expert` (rules a
developer chose for the task in advance, delivered the same way as `sf-hook`).
`--crowd DIR` (repeatable) installs extra skills in every arm, and `--task` can be
repeated for a suite; results are summarized per task. Paid runs
need an explicit `--model`, a behavioral grader, and a reviewed expert list for
`sf-expert`; `--freeze` locks the conditions across reruns. Read [docs/BENCHMARK_PROTOCOL.md](docs/BENCHMARK_PROTOCOL.md) first.

## Current coding library

| Module | Source | Status |
|---|---|---|
| coding-core | Authored; inspired by Ponytail and Superpowers | provisional |
| systematic-debugging | obra/superpowers @ 5bf4e78 (MIT) | provisional |
| test-driven-development | obra/superpowers @ 5bf4e78 (MIT) | provisional |
| react-performance | vercel-labs/agent-skills @ 063bee9 (MIT per skill metadata) | provisional |
| postgres | supabase/agent-skills @ 8331f91 (MIT) | provisional |
| verification-before-completion | obra/superpowers @ 5bf4e78 (MIT) | candidate (not exported; core covers it) |

Modules keep their original text, license and attribution (see each `SOURCE.json`).
Library modules are stored as `MODULE.md`, not `SKILL.md`, so Claude Code never
registers them as separate skills. Procedural guides are split into sections when
loaded; the files themselves are not edited.

## Building the library

The pipeline is **curation database → versioned export → lightweight runtime**.
`forge/sf.py` pins sources at exact commits, records them in a local SQLite database,
and exports `plugin/library/index.json`, including rule relations. The plugin reads
only the export. Benchmark runs stay as raw JSONL evidence until an ingestion step
is worth building. See [docs/DATABASE.md](docs/DATABASE.md). To add or change a
module, edit `forge/curation/coding.json`, then `import` and `export` again.

Do not hardcode `python3` in anything the agent runs: on Windows it is often a
Microsoft Store alias that prints "Python was not found" **and exits 0**.

## Repo layout
- `plugin/`: what users install (hook, skill, retriever, library)
- `forge/`: library builder (`sf.py`), A/B runner (`ab.py`), routing scorecard, grader validator, crawler stub
- `benchmarks/`: routing cases, coding tasks with hidden graders, and, kept outside the task
  folders so the agent never sees them, reference/broken solutions and expert rule selections
- `tests/`: retrieval, delivery, hook, runner and builder tests
- `docs/`: protocol and database notes; `docs/history/` holds earlier handoffs and reviews
- [STATUS.md](STATUS.md): where things stand. [ROADMAP.md](ROADMAP.md): what is not built.
