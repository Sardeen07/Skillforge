# Held-out routing set

**Status (2026-11-05):** `cases.jsonl` holds 74 cases (64 needing guidance, 10 unrelated),
frozen at sha256 `7b3b931609ad01608cebbf8563b57e0632d7e3c7043e4d3be374dbe4a3f40811` and
committed before any retrieval tuning on the 691-rule library. It was written by the same
author (Claude) who drafted the authored rule packs, from the rule catalog but without
looking at retrieval output, so it is *weaker* than the independent set described below:
it guards against tuning to the cases, not against the author's vocabulary matching the
rules'. An independent set from someone who has not read the library is still wanted.
Scores are reported once per retriever version; misses are not used to tune.

`benchmarks/retrieval/dev.jsonl` was read many times while the retriever was built and
tuned, so its score is optimistic. This folder is for a set nobody has tuned against.

## Who writes it

Someone who has **not** read the SkillForge code, the rule files, or the development
cases: a friend, a colleague, a tutoring student. Give them only this brief:

> Write 30+ one- to three-sentence messages you might send a coding assistant about a
> real problem. About a third should be about a Postgres database, a third about a
> React or Next.js app, a few about debugging or tests, and at least 8 about
> something else entirely (docs, CSS, git, config, a different language). Describe
> what you see going wrong, the way you would to a colleague. Don't name a fix.

## How to label it (before running anything)

1. Save their messages as `prompts.txt`, one per line, unedited.
2. Open the catalog (`node forge/py.mjs plugin/skills/skillforge/scripts/compose.py --catalog`)
   and, for each prompt, write down which rules a good engineer would want in hand.
   Use `[]` when no rule fits. Do this **before** running the scorecard on them.
3. Save as `cases.jsonl`, the same shape as the development set:

   ```json
   {"mode": "coding", "task": "...", "expect": ["postgres"], "rules": [["postgres/data-pagination"]]}
   {"mode": "coding", "task": "...", "expect": [], "rules": []}
   ```

   Each entry in `rules` is one need; list alternatives inside it when more than one
   rule would do.

## How to use it

```sh
npm run retrieval -- --cases benchmarks/heldout/cases.jsonl -v
```

Run it once per retriever version you want to report, and record the number. Do not
change the retriever in response to individual held-out misses. When you start
tuning against these cases, they have become development cases: move them into
`benchmarks/retrieval/dev.jsonl` and get a fresh held-out set.
