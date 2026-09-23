# SkillForge

A Claude skill that maximizes session efficiency by composing vetted, benchmarked skills based on what the task needs.

## How it works
1. Pick a mode (coding, debugging, testing, writing, research). Each mode has default skills, e.g. coding uses Ponytail.
2. Break the task into sub-tasks.
3. `compose.py` filters the local library, ranks matches by benchmark score, and prints one compact brief.

Only that brief enters Claude's context; the library itself costs disk, not tokens.

## Install (Claude Code)
```
/plugin marketplace add <your-org>/skillforge
/plugin install skillforge@skillforge
```

## Repo layout
- `plugin/`: what users install (router skill, commands, and the vetted `library/`)
- `forge/`: build pipeline (crawler, scanner, dedupe, Docker runner, scoring); never shipped
- `benchmarks/tasks/`: task repos with hidden tests
- `data/`: local SQLite database (gitignored)

## Roadmap
- [ ] Phase 1: database (`forge/schema.sql`)
- [ ] Phase 2: crawler (Skills Directory API + GitHub)
- [ ] Phase 3: security scanner
- [ ] Phase 4: benchmark tasks
- [ ] Phase 5: Docker runner
- [ ] Phase 6: update loop
- [ ] Phase 7: scoring + results table
- [ ] Phase 8: build-library into plugin/library

## Credits
Skills in `plugin/library/` keep their original licenses; see each entry's `source` and `license`.
