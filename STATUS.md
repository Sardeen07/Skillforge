# Status

Last updated 2026-09-23. This is the one current status file. Earlier handoffs and
reviews are in [docs/history/](docs/history/).

## Where things stand

**The hypothesis:** handing Claude a small, well-chosen set of curated rules produces
better code per dollar than native skill loading. That is untested. The project can now
*diagnose* where a benefit is won or lost, but it has not yet shown that SkillForge
improves any task outcome.

What the evidence so far does and does not say:

- Research suggests agents pick the wrong skill more often as libraries grow, and that
  optional skills often go unused. That motivates the project; it does not show
  SkillForge fixes it.
- Published results on skills point both ways. Some benchmarks report large average
  gains from curated skills, while a software-engineering benchmark cited in review
  found about a 1% average gain, with most skills changing nothing (not verified here).
  **Which guidance is curated may matter as much as how it is retrieved.**
- A small library is not proof SkillForge must lose, and keyword experiments on a few
  dozen development prompts are not proof keyword retrieval has hit a ceiling.

**Architecture work is paused.** The next step is a small, frozen, paid comparison;
its failures decide what changes next.

## Grader

`pg-queue-throughput` now uses **grader v2**. With a Postgres available (embedded via
`pgserver`, from `requirements-dev.txt`), three of its four checks observe behavior
against a real throwaway database:

| Check | What v2 observes |
|---|---|
| skip-locked | 4 concurrent workers each charge 8 jobs exactly once; a job locked by another worker is skipped at once, not waited on or errored |
| short-transaction | no row lock on the job is held while the payment call runs |
| fk-index | after the migrations run, an index led by `orders.customer_id` exists |
| keyset-pagination | still static (SQL literals, comments removed): the cursor function may have any name |

`npm run graders` validates 10 solution variants in both modes (behavioral and the
static fallback): 2 correct ones score 4/4, including a correct fix written differently
(`CREATE INDEX CONCURRENTLY`), and 8 broken ones each fail the check they target. What
the behavioral failures observed: without row locks, workers charged customers twice
(job 1 four times); with plain `for update`, a claim stalled behind a locked job; with
the charge inside the transaction, the lock was held during payment. The comment-only
fixes that fooled v1 are **permanent negative fixtures**.

`react-waterfall` and `binary-search` are not validated.

## Offline routing (development cases, seen while tuning)

| Set | Result |
|---|---|
| Development, 38 cases + benchmark paragraph | rule recall@4 **58.1%**; module hit 29/39 |
| Selected rules on that set | **27 relevant, 37 unnecessary (precision 42.2%)** |
| Prompts that needed guidance and got none | 5/39 |
| Supporting rules (declared dependencies) | 7 deliveries, ~1,400 estimated tokens, all TDD steps: to be reviewed |
| Explicitly mixed (two technologies), 3 cases | recall 66.7%; each gets both technologies where the evidence qualifies |
| Ambiguous and follow-up prompts, 4 cases | 3/4 abstain |
| Unrelated prompts (react,postgres stack) | 6/6 abstain |
| Old router, same labels | recall 35.9% |

Precision is now pooled over every delivered rule (the earlier 46.4% averaged per case,
which weighted a one-rule brief the same as a four-rule one). Supporting rules are
counted separately: neither excused nor counted as unnecessary, but listed with their
cost so each declared dependency can be reviewed. Every number above is from cases
visible while tuning, so it is an upper estimate until a held-out set is scored.

The main uncertainty: **whether the safeguards improve useful selection or mostly
suppress output.** That is why abstention, mixed and ambiguous prompts are reported
beside precision, and why the paid runs report correctness, abstention, cost and
latency together.

## What changed in the latest pass (second external review)

- **Grader hole fixed:** grader v2 (above), validated in both modes. Broken variants
  must fail their relevant checks; overlapping failures are allowed and reported.
- **Ambiguous vs explicitly mixed:** "Next.js" now counts as React (it didn't, so a
  mixed prompt lost its React half entirely), and each technology a sentence names gets
  its best qualifying rule before the stronger technology fills the remaining slots.
  Ambiguous prompts (no technology named, evidence split) still abstain. Regression
  sets: `retrieval-mixed.jsonl`, `retrieval-ambiguous.jsonl`.
- **Delivered is not the same as available:** the hook keeps per-session state. A
  follow-up with context intact adds nothing; the same follow-up after compaction or a
  resumed session re-delivers the last active rules once; a substantive new prompt that
  matches nothing drops them (a change of task); `/clear` starts over. `/forge-status`
  shows previously delivered vs active rules and says the hook cannot see what survived.
- **Controlled comparison:** hook arms record which rules arrived and whether each was
  byte-identical to the library; `sf-expert` also checks every intended rule arrived.
- **Frozen conditions:** `--freeze FILE` locks task, grader version, guidance inventory,
  expert list, model, tools, crowd and budget across reruns.
- **Gates on paid runs:** no static grading when a behavioral grader exists
  (`--allow-static-grader` overrides), and no `sf-expert` until the list is reviewed.
- **Precision split** into relevant, unnecessary and supporting, plus no-guidance counts.
- The per-task A/B summary prints correctness, no-guidance attempts, cost, latency and
  grader mode together.

## Known limits

- One mixed case gets half credit: "deep pages" misses the rule about "deeper pages"
  (a word-form gap), so no Postgres rule clears the threshold, and none is invented.
- "The orders page is slow" still gets a pagination rule: on word evidence alone,
  Postgres outscores React, so the ambiguity rule doesn't fire.
- Session restore is a heuristic: "follow-up" means a prompt with fewer than two
  content words. The hook cannot see the context window.
- Only `pg-queue-throughput` can tell arms apart; one task is not a product claim.
- No hook variant has run inside a live Claude Code session yet.

## Next feedback loop

1. **Expert review.** A second developer reviews `benchmarks/expert/pg-queue-throughput.json`
   without seeing model output, and records it under `review`.
2. **Freeze and run small:** `none, native, sf-expert, sf-hook` on `pg-queue-throughput`,
   5 repeats, one pinned model, with `--freeze`. Command in `docs/BENCHMARK_PROTOCOL.md`.
3. **Inspect every failure** (transcript, `delivery_check`, grader output), file it under
   retrieval, delivery, guidance, budget, execution or grader, and change one layer.
4. Only then: the held-out routing set, a second validated task, and the delivery,
   catalog and library-growth comparisons.
