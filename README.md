# SkillForge

SkillForge picks, deduplicates and compacts the Claude skills that actually win benchmarks, so Claude carries less and does better.

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

Requires Python 3 and git. From the repo root:

```
python3 forge/sf.py migrate                              # create/upgrade data/skillforge.db
python3 forge/sf.py import forge/curation/coding.json    # pin sources, copy modules, record them
python3 forge/sf.py list                                 # modules, status, overlap group, est. tokens
python3 forge/sf.py trace systematic-debugging           # module -> exact source repo/commit
python3 forge/sf.py export                               # write plugin/library/index.json
python3 -m unittest discover tests                       # rule and pipeline tests
```

All commands are safe to repeat. To add or change a module, edit `forge/curation/coding.json`, then import and export again.

Try the composer:
```
python3 plugin/skills/skillforge/scripts/compose.py --mode coding \
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

## Benchmark plan

Same tasks, same model, repeated runs, comparing four arms: no skills; the same skills installed normally; SkillForge with original modules; SkillForge with compacted modules. Planned runner: Harbor with SkillsBench-style tasks. The `runs` table records arm, composition, model, settings, task version, tokens (including cached), cost, and pass / fail / harness error, with unknowns left empty rather than zero.

## Repo layout
- `plugin/`: what users install (router skill, composer, library)
- `forge/`: library builder (`sf.py`, migrations, curation files, crawler stub)
- `tests/`: composer rules and import pipeline tests
- `data/`: local SQLite database and pinned source checkouts (gitignored)

## Credits
Modules keep their original text, license and attribution; see each module's `SOURCE.json`.
