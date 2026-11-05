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

> Status: working pipeline with a 691-rule library and offline benchmarks, **not yet
> benchmarked against native skills with a model**. Every rule's
> evidence status is `untested` until measured runs show it helps.

## How it works

- **Rules are the unit.** A rule is one curated reference file (e.g.
  `postgres/lock-skip-locked`) or one section of a procedural guide (e.g.
  `systematic-debugging/phase-1-root-cause-investigation`). The exported library has 691 rules across 64 modules (retrieval is local and deterministic).
- **Each rule carries metadata**, declared by hand in `forge/curation/coding.json`:
  applicability (technologies), `requires` (steps that must come with it), `conflicts`,
  provenance (pinned source and license) and evidence status. A later step of a
  procedure is delivered together with the steps before it, or not at all.
- **Retrieval** (`retrieval.py`) is local, deterministic BM25 over each rule's title, tags,
  keywords and text, ranked sentence by sentence. Technologies named in the prompt (from
  `technologies.json`: aliases such as `k8s`, `PostgreSQL`, `Next.js`, with implications such
  as Next.js → React) or found in the project's manifests (package.json, requirements,
  pyproject, go.mod, Cargo.toml, Maven/Gradle, Gemfile, composer.json, pubspec, Dockerfile,
  Terraform, GitHub workflows) reorder and demote rules but never select one on their own.
  A rule must clear an evidence threshold and match at least two prompt words; a prompt that
  names several technologies gets each one's best rule first. When evidence is split between
  technologies nothing technology-specific is guessed (technology-agnostic rules still
  apply), and weak or vague prompts get nothing. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- **Delivery is the open question**, so it is a switch, not a decision
  (`SKILLFORGE_HOOK`):

  | Variant | What enters context | Default |
  |---|---|---|
  | `off` | Only the SkillForge skill; Claude decides when to call it | yes |
  | `brief` | A hook injects the selected rules on each prompt that matches | |
  | `catalog` | A hook injects a bounded module catalog once; Claude can fetch one module catalog or selected rules by ID | |
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
Requires Python 3.9+ on the PATH (`python3`, `python` or `py`; the stock macOS `python3`
works). No packages, network access or API key are needed at runtime. The SkillForge skill
is available immediately; the automatic hook is off unless you set `SKILLFORGE_HOOK`:

| Variable | Values | Default |
|---|---|---|
| `SKILLFORGE_HOOK` | `off`, `brief`, `catalog`, `fixed` | `off` |
| `SKILLFORGE_HOOK_BUDGET` | estimated tokens per injected brief (200-50,000; invalid values fall back) | 2400 |
| `SKILLFORGE_STACK` | comma-separated technologies, overriding manifest detection | detected |
| `SKILLFORGE_LOG` | where selection logs go | `~/.skillforge/compose.log` |
| `SKILLFORGE_SYNONYM_WEIGHT` | opt-in query expansion (measured: small recall gain, more false positives) | 0 |

With the hook on and no usable Python, or on any internal error, the hook prints nothing and
exits 0: it never blocks a prompt. `/forge-status` shows what the last brief delivered and why.
Troubleshooting is in [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Try it

```sh
py=forge/py.mjs      # picks a working python3 or python for you
node $py plugin/skills/skillforge/scripts/compose.py "Build a scalable Next.js application with PostgreSQL, Redis caching, JWT authentication, and optimized database queries."
node $py plugin/skills/skillforge/scripts/compose.py --catalog            # module overview
node $py plugin/skills/skillforge/scripts/compose.py --catalog redis      # one module's rules
node $py plugin/skills/skillforge/scripts/compose.py --rule postgres/data-pagination
node $py plugin/skills/skillforge/scripts/compose.py --status             # what the last brief delivered, and why
```

The first command delivers, within budget, the coding core plus rules for several of the
concerns it names (Next.js data loading, PostgreSQL/SQL queries, Redis caching, JWT
verification), and prints which were dropped and why to the log.

## Measure it

```sh
python -m pip install -r requirements-dev.txt   # optional: embedded Postgres for one behavioral grader (use a .venv)
npm test                     # unit, integration, hook, runner, scanner, grader and benchmark-integrity tests
npm run validate:library     # schema, provenance, license, reference hosts, duplicates, relations, safety
npm run retrieval:suite      # recall@4, precision, NDCG@4, abstention, brief size, latency on all dev sets
npm run retrieval:heldout    # the frozen held-out set (report once per retriever version; never tune on it)
npm run sweep                # parameter sweep over the dev sets only
npm run graders              # every task grader passes its reference and fails its broken variants
npm run cost                 # offline: guidance tokens each delivery arm adds, per task prompt
npm run ab -- --dry-run --arms none,native,skillforge,sf-hook,sf-catalog,sf-expert
```

Measured results and how to read them are in [docs/BENCHMARKS.md](docs/BENCHMARKS.md).
In short (2026-11-05): on the development sets the hook's brief reaches 80-90% of labeled
needs with 64-79% precision and abstains on 44/50 unrelated and 30/30 vague prompts; on the
frozen held-out set 90.6% recall, 77.2% precision, 10/10 abstained. On the 28 real task
prompts it is much weaker (55% recall, 21% precision). **No paid model comparison has been
run**, so nothing here shows better code or lower API cost; offline, the hook adds ~750
estimated tokens of guidance per task prompt against ~4,600 for loading the same library as
native skills.

`forge/ab.py` runs real Claude Code sessions in isolated throwaway projects. Arms:
`none`, `native` (the same modules as ordinary skills), `skillforge` (skill only),
`sf-modules` (delivery ablation), `sf-hook`, `sf-catalog`, and `sf-expert` (rules a
developer chose for the task in advance, delivered the same way as `sf-hook`). It records
input, output and cached tokens, cost, turns, per-check grader results and the rules each
arm received. Paid runs need an explicit `--model`, a behavioral grader, and a reviewed
expert list for `sf-expert`; `--freeze` locks the conditions across reruns. Read
[docs/BENCHMARK_PROTOCOL.md](docs/BENCHMARK_PROTOCOL.md) first.

## Current coding library

691 rules in 63 modules plus the coding core (`npm run validate:library` prints the
statistics). Every rule is `evidence: untested`.

| Source | Modules | Rules | Provenance |
|---|---:|---:|---|
| Authored packs (`modules/*/RULES.md`) | 57 | 515 | SkillForge text (MIT), each rule citing the official documentation or standard it was checked against; drafted with Claude, **pending human review** |
| vercel-labs/agent-skills | 3 | 114 | react-performance @ 063bee9, react-native and react-composition @ 1a2c79d (MIT per skill metadata) |
| supabase/agent-skills | 1 | 31 | postgres @ 8331f91 (MIT) |
| obra/superpowers | 2 | 31 | systematic-debugging, test-driven-development @ 5bf4e78 (MIT) |

Coverage: Python, JavaScript, TypeScript, Java, C++, C, Rust, Go, Swift, Kotlin, PHP, Ruby,
C#, SQL; React, Next.js, Vue, Angular, Svelte, HTML/CSS, Tailwind, accessibility, web
performance, front-end state and component architecture; Node/Express, FastAPI, Django,
Flask, Spring Boot, REST and GraphQL API design, authentication and authorization,
distributed systems, caching and background jobs; PostgreSQL, MySQL, SQLite, MongoDB, Redis
and database design; LLM applications (prompting, RAG, embeddings, vector search, agents,
tool calling, evaluation, inference, fine-tuning, token and context management, AI
security) and ML engineering; Docker, Kubernetes, CI/CD and GitHub Actions, AWS/GCP/Azure,
Terraform, Linux and networking, observability; architecture, security, testing, TDD,
debugging, code quality and review, concurrency, error handling, profiling and memory;
SwiftUI/UIKit, Android, Flutter, React Native and mobile architecture.

Imported modules keep their original text, license and attribution (`SOURCE.json`) and are
stored as `MODULE.md`, not `SKILL.md`, so Claude Code never registers them separately.
`trailofbits/skills` (CC-BY-SA-4.0) and `anthropics/skills` (no repository license) were
considered and not imported. How to add rules: [docs/CONTRIBUTING_LIBRARY.md](docs/CONTRIBUTING_LIBRARY.md).

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
- `forge/`: library builder (`sf.py`), A/B runner (`ab.py`), routing scorecard, grader validator, skill scanner (`scan.py`), crawler stub
- `benchmarks/`: routing cases, coding tasks with hidden graders, and, kept outside the task
  folders so the agent never sees them, reference/broken solutions and expert rule selections
- `tests/`: retrieval, delivery, hook, runner and builder tests
- `docs/`: protocol and database notes; `docs/history/` holds earlier handoffs and reviews
- [STATUS.md](STATUS.md): where things stand. [ROADMAP.md](ROADMAP.md): what is not built.
