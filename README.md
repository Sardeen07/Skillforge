# SkillForge

SkillForge selects task-relevant instructions from a pinned skill library and delivers them in one bounded brief. Better model outcomes and lower total cost remain unproven.

Claude already loads skills on demand. SkillForge's job is deciding **which** instructions deserve to load: one installed entry instead of many, one provider per capability, and only modules that earn their tokens.

> Status: working pipeline, **not yet benchmarked**. Every module is `provisional` until runs recorded in the database show it helps.

## How it works

- **Coding core** (~200 tokens, estimated) loads for every coding task: `plugin/library/core/coding.md`.
- **Modules** sit on disk until a sub-task needs them: debugging, testing, React performance, Postgres.
- The composer picks at most one module per overlap group, per sub-task, within a token budget, and may pick none.
- Library modules are stored as `MODULE.md` (not `SKILL.md`) so Claude Code never registers them as separate skills.

## Install (Claude Code)
```
/plugin marketplace add Sardeen07/Skillforge
/plugin install skillforge@skillforge
```

## Building the library

Requires Python 3.10+, git and Node (Node only for the `npm` wrappers). From the repo root:

```
py=forge/py.mjs                                          # picks python3 or python for you
node $py forge/sf.py migrate                             # create/upgrade data/skillforge.db
node $py forge/sf.py import forge/curation/coding.json   # pin sources, copy modules, record them
node $py forge/sf.py list                                # modules, status, overlap group, est. tokens
node $py forge/sf.py trace systematic-debugging          # module -> exact source repo/commit
node $py forge/sf.py export                              # write plugin/library/index.json

npm test                                                 # rule, pipeline and portability tests
npm run retrieval                                        # routing scorecard
npm run ab -- --task benchmarks/tasks/pg-queue-throughput --repeats 3 --model YOUR_MODEL_ID
```

Call `python3` (macOS/Linux) or `python` (Windows) directly if you prefer. Do not
hardcode `python3` in anything the agent runs: on Windows it is usually a Microsoft
Store alias that prints "Python was not found" **and exits 0**, so the failure is
silent — this masked an entire benchmark arm until it was caught.

All commands are safe to repeat. To add or change a module, edit `forge/curation/coding.json`, then import and export again.

Try the composer:
```
node forge/py.mjs plugin/skills/skillforge/scripts/compose.py --mode coding \
  --subtask "find why the search list rerenders" --subtask "fix the bug" --stack react
```
Selection reasons and misses are logged to `~/.skillforge/compose.log`, not the brief.

## Current coding library

| Module | Source | Status |
|---|---|---|
| coding-core | Authored; inspired by Ponytail and Superpowers | provisional |
| systematic-debugging | obra/superpowers @ 5bf4e78 (MIT) | provisional |
| test-driven-development | obra/superpowers @ 5bf4e78 (MIT) | provisional |
| react-performance | vercel-labs/agent-skills @ 063bee9 (MIT per skill metadata) | provisional |
| postgres | supabase/agent-skills @ 8331f91 (MIT) | provisional |
| verification-before-completion | obra/superpowers @ 5bf4e78 (MIT) | candidate (not exported; core covers it) |

## Benchmarking

`forge/ab.py` runs one task across three default arms, each in a throwaway project with its own
`CLAUDE_CONFIG_DIR`, so the machine's installed plugins cannot leak in:

| Arm | Gets |
|---|---|
| `none` | nothing — the floor |
| `native` | the library's modules installed as ordinary skills |
| `skillforge` | the real `plugin/`, so the router calls `compose.py` |

```
npm run ab -- --task benchmarks/tasks/pg-queue-throughput --repeats 3 --model YOUR_MODEL_ID
```

Read the `brief` column first. `skill_used` only means the router was invoked; `brief`
means a compose tool result contained a brief header; it can still be core-only. A missing `brief` means delivery was not verified. Keep that attempt in the
report and inspect its transcript; do not discard inconvenient outcomes.

Then read `score` before `cost`: cheaper but wrong is not cheaper.

**A task only discriminates when the model's default answer is wrong.** See
`benchmarks/tasks/README.md` — `react-waterfall` is solved at full marks by every arm,
including `none`, so it measures prompt size rather than skill quality.

The `runs` table has fields for arm, composition, model, settings, task version, tokens
(including cached), cost, and pass / fail / harness error. The current runner
writes JSONL and does not populate that table automatically. Unknowns stay empty.

## Repo layout
- `plugin/`: what users install (router skill, composer, library)
- `forge/`: library builder (`sf.py`, migrations, curation files, crawler stub)
- `tests/`: composer rules and import pipeline tests
- `data/`: local SQLite database and pinned source checkouts (gitignored)

## Credits
Modules keep their original text, license and attribution; see each module's `SOURCE.json`.

## Rule delivery and controlled experiments

The default now retrieves rule titles, tags and introductory symptoms locally, then
inlines up to four complete matching rules per selected module. It omits that
module's index when rules match; procedural guides and required modules stay whole.
No LLM call, embeddings service, or database is needed at runtime. Source files,
licenses and attribution remain intact. This is extractive selection, not semantic
summarization. Cross-module semantic deduplication is not implemented.

```sh
npm run retrieval -- --baseline
npm run retrieval
npm run retrieval -- --cases benchmarks/retrieval-negatives.jsonl --stack react,postgres
node forge/py.mjs plugin/skills/skillforge/scripts/compose.py --subtask "workers block each other in the queue" --explain data/selection.json
npm run ab -- --dry-run --arms none,native,skillforge,sf-modules,sf-keywords
```

- `--delivery rules|modules` changes inline rules versus full modules plus rule paths.
- `--routing references|keywords` changes retrieval versus the original keyword mechanism.
- `--budget` limits the complete serialized brief using `ceil(characters / 4)`,
  including provenance. This is an estimate, not a tokenizer-enforced limit.
- `--explain FILE` records delivered, cached, duplicate and budget-skipped units.
- Session caching is **off by default**. Use a unique `--session FILE` only within
  one conversation. Keys hash individual file contents, so new rules from a
  previously used module still load. Use `--reset` after compaction.

The runner requires an explicit `--model` for actual runs. It appends attempts to
`data/ab-results.jsonl` including hashes, settings, errors and unknown costs. Use a
new output filename for each experiment. `--keep` retains transcripts and task
outputs; temporary copied credential directories are removed on every exit.
The native arm includes the same exported eligible modules, without the SkillForge
router or authored core. It no longer includes the excluded verification candidate.

See [review and measured evidence](docs/REVIEW.md),
[experiment protocol](docs/BENCHMARK_PROTOCOL.md), and
[database setup](docs/DATABASE.md). No new model A/B results are claimed.
