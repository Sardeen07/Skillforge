# Status

Last updated 2026-11-05. Detailed results: [docs/BENCHMARKS.md](docs/BENCHMARKS.md). Release
record: [docs/RELEASE_REPORT.md](docs/RELEASE_REPORT.md). Earlier handoffs: [docs/history/](docs/history/).

## Where things stand

**The hypothesis** (a small, well-chosen set of curated rules gives better code per dollar
than native skill loading) **is still untested with a model.** What exists now:

- A 691-rule library in 63 modules plus the coding core: 515 authored rules in 57 packs
  (each citing the official reference it was checked against, drafted with Claude and
  **pending human review**) and 176 rules from five pinned, MIT-licensed upstream modules.
  Every rule is `evidence: untested`. The validator passes (0 errors, 2 reviewed notices).
- A deterministic local retriever with technology detection, a coordination guard,
  multi-technology coverage, an ambiguity guard and a brief-level relevance cut, tuned on
  development sets only. No LLM or embedding calls; ~3 ms per prompt after load, ~0.2 s
  per prompt end to end through the hook.
- A benchmark suite: 109 dev, 30 mixed, 20 security, 20 performance, 28 task-prompt,
  50 negative and 30 ambiguous routing cases; a 74-case held-out set frozen before tuning;
  30 behavioral coding tasks (29 with validated graders); an offline context-cost tool;
  and the A/B runner for paid comparisons.

## Measured (offline, no model)

| | Recall@4 | Precision | Abstained |
|---|---:|---:|---:|
| Development sets (dev, mixed, security, performance) | 80-90% | 64-79% | - |
| Real task prompts (28) | 55.4% | 21.4% | - |
| Unrelated prompts (50) / vague prompts (30) | - | - | 44/50 / 30/30 |
| **Held-out (74, frozen before tuning, same author as the rules)** | **90.6%** | **77.2%** | **10/10** |

Offline context per task prompt: the hook adds ~750 estimated tokens of guidance; the same
library as native skills ~4,600 (of which ~2,500 is the always-present skill listing). This
is input text size, not model usage or cost.

## What these numbers do not show

- **Nothing about code quality or API cost.** No paid run has been made. Output tokens,
  cached tokens, request counts, task success and cost per arm are unknown.
- The held-out set shares its author with the authored rules, so it overstates retrieval on
  real prompts. The task-prompt set (55% / 21%) is the more realistic signal and the main
  retrieval weakness: long prompts with code identifiers and symptom words the rules lack.
- Whether the new behavioral tasks discriminate between arms (a model's default answer must
  be wrong) has been designed for, not measured.
- Authored rules have automated checks (structure, references on reviewed hosts, safety
  scan, duplicates) but no human technical review yet.

## First paid data (2026-11-09)

A 4-session smoke test on Opus 5.5 (`pg-queue-throughput`, one session per arm): every arm
scored 4/4, costs $0.20-0.27 per session, and the no-guidance arm was cheapest. The task no
longer discriminates on this model. Details: docs/BENCHMARKS.md §4.

## Next feedback loop

0. **Build harder tasks.** The `none` arm solved all 30 tasks on Opus 5.5 (one attempt each,
   $3.33; two partial scores were grader bugs, now fixed). Until some task defeats the
   unguided model, a paid comparison can measure only the cost of extra context, not a
   quality gain.
1. **Paid comparison, small and frozen:** `none, native, sf-hook, sf-expert` on 4-6 tasks,
   5 repeats, one pinned model, `--freeze` (command in docs/BENCHMARKS.md §4). Needs expert
   lists reviewed for each task. Record tokens (input/output/cached), cost and grader checks.
2. **Human review** of the authored packs, highest-traffic modules first; record reviewer and
   date in each `SOURCE.json`.
3. **Independent held-out set** from someone who has not read the library.
4. Improve routing on real task prompts (identifier-aware tokenization, symptom vocabulary
   in `keywords`), measured on the `tasks` set and then the held-out set once.
