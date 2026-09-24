> **Archived.** Superseded by [STATUS.md](../../STATUS.md). Paths and numbers below describe the
> code as it was then (module-first routing, 40 tests); evidence files moved to `history/evidence/`.

# Latest handoff: bounded rule delivery review

The notes below describe the previous local session and are retained as history.
For current behavior, read `docs/REVIEW.md` and `docs/BENCHMARK_PROTOCOL.md`.

- Uploaded local baseline reproduced: 18 tests passed; 7/38 routing cases hit.
- Updated routing: 24/38 on the unchanged development set; all 7 old hits retained.
- CLI defaults to reference-aware retrieval and complete inline rule delivery.
- Session caching is now opt-in; never reuse a session path across conversations.
- A/B requires `--model`; new arms isolate routing and delivery. Attempts append
  to JSONL, not SQLite. Native inventory now matches eligible exported modules.
- Original task graders are unchanged and still have static-check limitations.
- No fresh model A/B was possible because Claude Code is absent here.
- Exact final validation output and per-case predictions are in `docs/evidence/`.

---

# SkillForge — session handoff

Written for whoever picks this up next (human or a fresh Claude session). Read this
first, then `README.md` for the product pitch.

## Where things stand

The previous session added measurement tooling but never got a valid reading out of it.
This session found out why, fixed it, and added a task that can actually tell the arms
apart.

### The bug that invalidated every earlier benchmark

`SKILL.md` told the agent to run `python3 .../compose.py`. On Windows `python3` is a
Microsoft Store alias that prints `Python was not found` **and exits 0**. So
`compose.py` never ran. The `skillforge` arm was running on the router's six lines of
text with no module content at all, while paying for the extra turns to invoke it. The
agent said so in its own transcript and nobody was reading transcripts:

> "The SkillForge helper script didn't run because Python isn't installed on this
> machine. I did the work without its guidance."

`skill_used` did not catch this: it matched the `Skill` tool *invocation*, which
happened. `ab.py` now reports a separate **`brief`** column that only goes true when
`compose.py` actually printed `# SkillForge brief:`, and warns loudly when the router
fired without producing one. **Read `brief` before anything else.**

### The benchmark had an unreachable ceiling

`react-waterfall` scored 2/3 for every arm, every time. The failing check was always
`no-barrel-import` — and the temp project contained only `page.tsx`, with no
`package.json` and no `components/`. Rewriting `from '@/components'` to a direct path
meant inventing an unverifiable path, which a careful agent refuses to do. The fixture
now ships a real component package, and the task is solved at 3/3 by every arm.

Which is the honest result: **`react-waterfall` does not discriminate.** Claude already
knows `Promise.all`, hoisted components and barrel imports. Do not use it to argue for
SkillForge.

### Other bugs fixed

| Bug | Symptom |
|---|---|
| `clone_url` mangled local paths | `C:\src\upstream` became `https://github.com/C:\src\upstream.git`; the import pipeline test failed on Windows |
| Unencoded `read_text()` throughout | cp1252 decode of UTF-8 modules; crashes the brief rather than degrading |
| `compose.py` wrote to a legacy console encoding | added `sys.stdout.reconfigure` |
| `ab.py setup()` copied only files | fixture subdirectories silently dropped |
| `--session /tmp/...` shared between runs | run 2 onward gets "already loaded" and no module text; each run now gets its own `TMPDIR` |
| `npm test` hardcoded `python3` | `forge/py.mjs` probes for a working Python 3 |

CI now runs on **ubuntu and windows**. Every bug above passed on Linux and failed on
Windows; a Linux-only matrix is why they survived this long.

## The task that does discriminate

`benchmarks/tasks/pg-queue-throughput` — a Postgres queue worker with four defects,
each chosen because the *obvious* fix is the wrong one:

| Check | The obvious answer | Why it is wrong |
|---|---|---|
| `skip-locked` | "add `for update`" | already there; needs `skip locked` |
| `short-transaction` | "wrap it in a transaction" | the transaction spans a 2-5s HTTP payment call |
| `keyset-pagination` | "index the order by" | `offset` still scans and discards skipped rows |
| `fk-index` | "the foreign key is indexed" | Postgres indexes primary keys only |

Verified both ways before use: **0/4 on the unfixed fixture, 4/4 on a hand-written
reference solution.** `tests/` now enforces the first half of that for every task, so
nobody ships another unfailable check.

## The real open problem: routing

The composer matches sub-tasks against hand-curated `applies` keyword lists. On raw
user phrasing it scores **hit 7/38 (18%), core-only 28/38**.

```
none   eight workers but throughput is the same as two    -> (core only)   want postgres
none   we hold a row lock while calling the payment api   -> (core only)   want postgres
none   the report is fine on page 2 and unusable on 900   -> (core only)   want postgres
```

Everything depends on Claude paraphrasing into library vocabulary before calling
`compose.py`. "speed up the **postgres query**" routes; "workers waiting on each other"
does not. When it misses, the run still succeeds — just with no module — and nothing
looks wrong. That is the single highest-value thing to fix, and keyword matching is
probably the wrong mechanism for it.

`SKILL.md` step 1 now tells Claude to name the technology in each sub-task, which is the
cheap half of the fix and costs one line of prompt. It is not the real fix. The real fix
is that a module should be reachable from the symptom a person actually reports, and
that is a retrieval problem, not a prompt problem. Note `--stack` currently only *boosts*
modules the sub-task already matched (see `relevance()`); letting it select would make
`postgres` load for every sub-task in a Postgres repo, including "update the README", so
it was deliberately left alone rather than changed without a measurement to justify it.

CI has a floor at 15% (`score_retrieval.py --min`). It is a regression guard sitting
just under the measured 18%, not a target. Raise it as routing improves; never lower it
to make a red build green.

## Both modules are tables of contents

Neither `react-performance` nor `postgres` MODULE.md contains actual guidance. The
react one lists 70 rule names; the postgres one does not even do that — it lists
category prefixes and says "read individual rule files".

The brief used to print the reference *folder* and the words "read only if needed".
Measured result: the agent opened nothing. It solved the two defects it already knew
(`skip-locked`, `fk-index`) and missed keyset pagination while
`references/data-pagination.md` sat unread in that folder.

`compose.py` now ranks a module's reference files against the sub-task and names the
top four, with absolute paths, telling the agent the module text is only an index.
Matching is on each rule's frontmatter `title` and `tags`, not its filename — the file
is `lock-skip-locked.md` but its tags say "queue, workers, concurrency", and a sub-task
about workers would never match the filename. `SKILL.md` step 5 was changed to match;
it previously said to open reference files "only if ... you need them", which argued
against the list the brief now hands it.

This is one function (`pick_references`) reusing the existing `words()` matcher, and it
does not touch module selection — the retrieval scorecard is unchanged at 18%.

## Gotchas already paid for

- **Read `brief`, not `skill_used`.** See above.
- **Never use `--safe-mode`.** It disables plugin skills, silently turning the
  skillforge arm into the none arm.
- **Plugin dirs must sit outside the working directory**, or the agent reads them as
  ordinary project files with Glob/Read.
- **`--tools` is a whitelist and must include `Skill`.** `ab.py` refuses to start
  without it.
- **`--output-format json` hides tool calls.** Activation detection needs
  `stream-json --verbose`.
- **Plugin skills are namespaced `plugin:skill`** — `skillforge:skillforge`.
- **`benchmarks/tasks/binary-search` hangs on its own bug** (`lo = mid` never
  advances). Anything running it needs a timeout.
- Run folders are deleted automatically; pass `--keep` to inspect `transcript.jsonl`.

## Next

1. Fix routing, or replace keyword matching. It is the bottleneck.
2. Feed real numbers into the `score` field in `index.json` — it is `None` for every
   module, so the score-based ranking tiebreak is inert.
3. Compact the modules. The fourth arm in the original plan (SkillForge with compacted
   modules vs. original modules) has never been run, and it is the arm that tests the
   project's actual thesis.
