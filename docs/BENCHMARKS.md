# Benchmarks

What is measured, how to reproduce it, and what it does and does not show. Every number
below came from the commands in this file on 2026-11-05 (macOS, Python 3.12). Raw outputs
are in [docs/evidence/](evidence/).

## 1. Offline routing (no model calls)

`npm run retrieval:suite` scores what the hook would actually deliver at its 2,400-token
budget. Each case labels the rules it needs (each need lists acceptable rule IDs); a case
with no labels must get nothing. Delivered rules are classified relevant, unnecessary, or
supporting (a declared dependency). Label patterns that match no rule are rejected (one dev
case had a dead pattern, `systematic-debugging#*`, and could never score; fixed).

| Set | Cases | What it is |
|---|---:|---|
| `dev` | 109 | 39 original development cases + 70 symptom-phrased prompts across the library |
| `mixed` | 30 | prompts naming two to four technologies or concerns (includes the directive's Next.js + PostgreSQL + Redis + JWT example) |
| `security` | 20 | security symptoms |
| `performance` | 20 | performance symptoms |
| `tasks` | 28 | the real `task.txt` prompts of the behavioral tasks (long, with code identifiers) |
| `negatives` | 50 | unrelated requests that must get no rule |
| `ambiguous` | 30 | vague prompts and follow-ups that must get no rule |
| `heldout` | 74 | 64 needing rules + 10 unrelated; frozen and committed **before** tuning (sha256 in [benchmarks/heldout/README.md](../benchmarks/heldout/README.md)) |

### Results (final retriever, 2026-11-05)

| Set | Recall@4 | Precision | NDCG@4 | Abstained | Mean brief (est. tokens) | of which unnecessary |
|---|---:|---:|---:|---:|---:|---:|
| dev | 79.8% | 63.9% | 0.774 | - | 521 | 67 |
| mixed | 80.8% | 64.0% | 0.775 | - | 761 | 221 |
| security | 90.0% | 69.2% | 0.863 | - | 437 | 38 |
| performance | 90.0% | 79.2% | 0.882 | - | 410 | 21 |
| tasks | 55.4% | 21.4% | 0.469 | - | 756 | 309 |
| negatives | - | - | - | 44/50 | 285 | 12 |
| ambiguous | - | - | - | 30/30 | 268 | 0 |
| **heldout** | **90.6%** | **77.2%** | **0.872** | **10/10** | 417 | 22 |

Brief sizes include the ~190-token coding core, which the hook omits when nothing matches.
Local retrieval takes ~3 ms per prompt once loaded; the hook end to end (Python start, load
691 rules, rank) takes ~0.2 s per prompt. With the hook off (the default) it costs nothing.

**Before this pass** (same 691 rules, 2026-11-03 settings, same sets): dev recall 79.8%,
precision 41.5%; negatives 35/50 abstained; ambiguous 28/30; mixed 85.8% recall, 48.3%
precision (the `tasks` set did not exist yet). The original 39-case dev set alone went from
51.3% recall / 26.1% precision (2026-11-03 report) to the numbers above.

### How to read these numbers

- **The held-out set is weaker than it looks.** It was frozen before tuning and scored once
  per retriever version, but it was written by the same author (Claude) who drafted the
  authored rules, so its vocabulary matches theirs. That is why it scores *higher* than dev.
- **The `tasks` set is the most realistic and the weakest:** 55% recall, 21% precision. Real
  prompts are long, name identifiers (`render_report in service.py`) and describe symptoms in
  words the rules do not use. This is the main open retrieval problem.
- An independent held-out set, written by someone who has not read the library, is still needed.

### Tuning record

All parameters were chosen with `npm run sweep` on the development sets only (never the
held-out set). Full tables: [evidence/sweep-2026-11-05.json](evidence/sweep-2026-11-05.json).

| Change | Effect on dev sets | Kept? |
|---|---|---|
| MIN_SCORE 10 → 12, RELATIVE 0.45 → 0.75 | precision ~41% → ~62%, abstention 79% → 92%, recall −4 pts | yes |
| Coordination guard: a rule must match 2 distinct prompt words | fewer single-word false positives at low thresholds; small effect at 12 | yes |
| Brief-level cut (BRIEF_RELATIVE 0.55): drop hits under 55% of the prompt's best | precision +4.6 pts, recall −1 pt | yes |
| Named-technology coverage protected from that cut; its own technology counts as a matched word | mixed recall 75.8% → 80.8% at equal precision | yes |
| Ambiguity guard falls back to technology-agnostic rules instead of nothing | dev recall +0.9, tasks recall +7 pts, no abstention loss | yes |
| Canonical names (`go`, `c`) and words like `express`, `node`, `rails`, `cargo` no longer name a technology | removes false technology detection ("let us go…") | yes |
| Curated synonyms (`synonyms.json`), weight 0.3 / 0.5 | recall +1.3 pts, abstention 92.5% → 86.2% | **no: off by default** (`SKILLFORGE_SYNONYM_WEIGHT`) |
| MIN_SCORE 14 | best F1, but twice as many prompts with no guidance | no |

Semantic (embedding) retrieval was not added: it needs a model download and a native
runtime, and the measured bottleneck (real task prompts) is vocabulary mismatch between
symptoms and rule text. An optional embedding scorer should be benchmarked against these
same sets before it is enabled by default.

## 2. Context cost per delivery arm (no model calls)

`npm run cost` estimates the guidance text each arm puts into context for the 28 task
prompts. Characters / 4, not a tokenizer count.

| Arm | Mean added tokens | Median | Max | Labeled needs covered |
|---|---:|---:|---:|---:|
| none | 0 | 0 | 0 | 0% |
| native (63 modules as skills; assumes the model loads exactly the right modules) | 4,589 | 4,339 | 6,851 | 100% (assumed) |
| skillforge (skill only, if called once) | 813 | 713 | 1,804 | 57% |
| sf-hook | 747 | 647 | 1,738 | 57% |
| sf-catalog (bounded catalog + correct fetches) | 1,227 | 1,196 | 1,651 | 100% (assumed) |
| sf-expert (exactly the labeled rules) | 442 | 399 | 1,168 | 100% |

The native skill listing alone is ~2,500 tokens per session for 63 modules, before any skill
is loaded. **This is not a cost result.** It does not include output tokens, cache reads,
number of requests, tool overhead or task success, and native and catalog coverage are
assumed perfect. It bounds the input side only: whether fewer guidance tokens mean lower
cost *and* equal or better code is exactly what the paid comparison must show.

## 3. Behavioral graders (no model calls)

`npm run graders` builds each task's reference solution and broken variants and checks that
the hidden grader gives the reference full marks and fails each broken variant on the check
it targets. 30 tasks; 29 validated (81 solution variants), `react-waterfall` not validated.

Bugs the validation caught while building the suite: a wrong expected value in the
money-rounding grader (0.30 × 8.25% rounds to 0.02, not 0.03); a ReDoS check that hung the
grader because the regex engine holds the GIL (now run in a subprocess); broken variants
that were too weak to fail (a chunked-commit variant, an as-completed ordering variant).

## 4. Paid model comparison

### Smoke test (2026-11-09): one session per arm, Opus 5.5, `pg-queue-throughput`

`--isolation flags` (operator's login; user settings, plugins, skills and MCP servers off,
checked per session from Claude Code's init event: no contamination in any session).

| Arm | Score | Cost | Turns | Output tokens | Cache read | Cache write | Seconds | Rules delivered |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| none | 4/4 | $0.198 | 7 | 4,784 | 68,931 | 11,105 | 54 | - |
| native | 4/4 | $0.269 | 10 | 5,579 | 115,776 | 16,732 | 64 | loaded the postgres skill |
| sf-hook | 4/4 | $0.235 | 8 | 5,242 | 98,649 | 13,802 | 62 | 3 of the 4 expert rules |
| sf-expert | 4/4 | $0.224 | 7 | 4,853 | 81,878 | 13,860 | 57 | the 4 expert rules |

Total: **$0.93** for four sessions. One session per arm supports no conclusion, but two
observations matter for the next run: (1) Opus 5.5 solved this task fully **without any
guidance**, so `pg-queue-throughput` no longer discriminates between arms on this model, and
the cheapest arm was the one with no guidance; (2) per-session cost is ~$0.20-0.27, so the
recommended 80-session run would cost about **$15-25**, not the $25-120 first estimated.
Before that run, the `none` arm should be run once on every task to find the tasks this
model actually fails; only those can show whether guidance helps.

### Discrimination check (2026-11-09): `none` arm on all 30 tasks, Opus 5.5

One session per task, no guidance, $3.33 in total ($0.08-0.20 per session, 4-7 turns).
28 tasks scored full marks. The two partial scores were **grader bugs, not model failures**:
`retry-with-backoff` rejected a correct "full jitter" schedule (it compared single runs
instead of averages), and `regex-redos`'s task text contradicted itself about newline
separators. Both graders were fixed and revalidated; re-grading the saved solutions gives
full marks. So **Opus 5.5 solves all 30 tasks without any guidance**, on one attempt each.

Consequence: with this model, no current task can show a quality benefit from SkillForge
(or from native skills); a comparison could only measure added cost. Discriminating tasks
must be harder: longer multi-file fixtures, defects whose obvious fix is wrong (as
`pg-queue-throughput` was for earlier models), or project-specific conventions the model
cannot know without guidance. Repeats would also be needed to catch occasional failures.
Raw rows: [evidence/ab-none-all-2026-11-09.json](evidence/ab-none-all-2026-11-09.json).

### Harder tasks (2026-11-09): 8 tasks with traps, `none` arm, 2 attempts each

Eight tasks whose obvious fix looks complete but misses a practice a library rule states
(overselling across worker processes, idempotency-key scoping and reuse, Retry-After as an
HTTP date, reset-token storage and revocation, cursor ties, tar symlink escapes, CSV formula
injection, log forging). Prompts describe symptoms only. Graders validated against the
reference and the "obvious fix" variant of each. 16 sessions, $1.99.

| Task | Unguided Opus 5.5 (2 attempts) | Trap missed | Hook delivers the trap's rule? |
|---|---|---|---|
| `csv-export` | 1/2, 1/2 | formulas left live (fixed quoting only) | yes (`security/csv-formula-injection`) |
| `reset-token-hardening` | 3/5, 3/5 | tokens stored raw; older links still work after a reset | yes (`auth/password-reset-tokens`) |
| `oversell-workers` | 2/2, 2/2 | - | no |
| `idempotency-hardening` | 4/4, 4/4 | - | yes |
| `retry-after-client` | 6/6, 6/6 | - | partly (no rule mentions the HTTP-date form) |
| `feed-cursor-ties` | 3/3, 3/3 | - | yes |
| `theme-archive-extract` | 3/3, 3/3 | - | yes |
| `login-audit-log` | 2/2, 2/2 | - | no |

**Two tasks discriminate:** the model consistently did what the prompt asked and stopped,
missing the practice nobody asked for. For both, the hook delivers the rule that covers the
trap, so these are the first tasks where a guided arm *could* score higher. Whether it does
is the next measurement. `security/csv-formula-injection` was added to the library while
designing `csv-export`; that is disclosed here because it means the rule exists *because of*
the task, which favors SkillForge on it.

The run also exposed a runner bug: a bare `PASS name` line swallowed the next line when
parsing, so a second failed check went unrecorded (scores were unaffected). Fixed, with a test.

### Full comparison (not run)

`forge/ab.py` runs real Claude Code sessions per arm in isolated projects and records input,
output and cached tokens, cost, turns, per-check grader results and the rules delivered.
It was **not run** for this release: it spends the operator's API budget and needs an
explicit model choice. Recommended first run (see [BENCHMARK_PROTOCOL.md](BENCHMARK_PROTOCOL.md)):

```sh
npm run ab -- --model <model-id> --arms none,native,sf-hook,sf-expert \
  --task benchmarks/tasks/pg-queue-throughput --task benchmarks/tasks/ssrf-url-check \
  --task benchmarks/tasks/deep-pagination-sqlite --task benchmarks/tasks/cache-stampede \
  --repeats 5 --freeze data/freeze.json
```

`sf-expert` additionally needs a reviewed `benchmarks/expert/<task>.json` for each task
(only `pg-queue-throughput` has one). Until such runs exist there is no evidence that
SkillForge changes task outcomes or total cost, and every rule stays `untested`.
