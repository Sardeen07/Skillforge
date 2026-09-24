# Fresh benchmark protocol

## Freeze before spending

Keep the current graders unchanged when comparing this patch. Record the exact
model ID, CLI version, source revision, task files and scorer version. The runner
records hashes, but you must select a model you can actually access. It does not
silently choose one. Replace `YOUR_MODEL_ID` below with that identifier.

Smoke-test without API use:

```sh
npm test
npm run retrieval -- --baseline
npm run retrieval -- --min 0.55
npm run graders
npm run ab -- --dry-run --arms none,native,skillforge,sf-modules,sf-hook,sf-catalog,sf-expert
```

## Before any paid run

### 1. Validate the grader

```sh
python -m pip install -r requirements-dev.txt   # embedded Postgres; once, ideally in .venv
npm run graders
```

Every task needs correct solutions that score full marks and plausible broken ones
(`benchmarks/solutions/<task>/`). A broken solution must fail the checks it targets
(`must_fail`) and keep passing the ones it gets right (`must_pass`); failing other
checks as well can be legitimate and is reported, not rejected. Graders that run
behaviorally against a database are validated in both modes: behavioral, and the
static fallback. A task marked NOT VALIDATED cannot support a claim.

`pg-queue-throughput` uses grader v2: concurrency, lock duration and the foreign-key
index are checked against a real throwaway Postgres. v1 gave full marks to `skip locked`
written only in a comment; that solution is now a permanent negative fixture.

### 2. Get the expert list reviewed

A second developer reviews `benchmarks/expert/<task>.json` without seeing any model
output, and records their name under `review`. Paid `sf-expert` runs refuse to start
until then.

### 3. Freeze the conditions

```sh
npm run ab -- ... --freeze data/<experiment>.freeze.json
```

The first run writes the task and grader hashes, grader version, guidance inventory,
expert lists, model, tools, crowd and hook budget; every later run with the same file
refuses to start if any of them changed. A new condition needs a new manifest and a new
output file. Paid runs also refuse a task whose grader needs Postgres when none is
available (`--allow-static-grader` overrides; report it if used).

## Arms

| Arm | What it tests |
|---|---|
| `none` | The floor: no skills. |
| `native` | The same eligible modules installed as ordinary skills. The practical comparator. |
| `skillforge` | The skill only (hook off). Claude must choose to call `compose.py`. |
| `sf-modules` | As `skillforge`, but full modules plus rule paths. Delivery ablation. |
| `sf-hook` | The hook injects the retrieved brief. Tests automatic injection, when the hook succeeds. |
| `sf-catalog` | The hook injects the rule catalog once; Claude fetches rules by ID. Tests model-side routing. |
| `sf-expert` | The hook injects rules a developer chose for the task beforehand (`benchmarks/expert/<task>.json`). The ceiling for selection. |

`skillforge` vs `sf-hook` changes only the delivery mechanism (same retriever, same
brief). `sf-hook` vs `sf-expert` changes only who selected the rules. `sf-hook` vs
`sf-catalog` changes who routes. Keep those comparisons separate. Injection proves the
text was in context, not that the model used it; read transcripts for that.

A combined catalog-plus-brief arm is deliberately absent. Build it only if both
variants do well separately.

## Order of experiments

```sh
# 1. Where is the benefit lost? Expert selection vs retrieval vs nothing vs native.
npm run ab -- --task benchmarks/tasks/pg-queue-throughput --arms none,native,sf-hook,sf-expert --model YOUR_MODEL_ID --repeats 5 --seed 17 --keep --freeze data/expert-ab.freeze.json --output data/expert-ab.jsonl

# 2. Does automatic injection beat optional invocation, with the same brief?
npm run ab -- --task benchmarks/tasks/pg-queue-throughput --arms skillforge,sf-hook --model YOUR_MODEL_ID --repeats 5 --seed 17 --keep --output data/delivery-ab.jsonl

# 3. Model-side routing.
npm run ab -- --task benchmarks/tasks/pg-queue-throughput --arms sf-hook,sf-catalog --model YOUR_MODEL_ID --repeats 5 --seed 17 --keep --output data/catalog-ab.jsonl

# 4. Library growth: unrelated distractors, then similar competing skills, in every arm.
npm run ab -- --task benchmarks/tasks/pg-queue-throughput --arms none,native,sf-hook,sf-catalog --crowd PATH/TO/UNRELATED --model YOUR_MODEL_ID --repeats 5 --seed 17 --keep --output data/crowd-unrelated.jsonl
npm run ab -- --task benchmarks/tasks/pg-queue-throughput --arms none,native,sf-hook,sf-catalog --crowd PATH/TO/UNRELATED --crowd PATH/TO/SIMILAR --model YOUR_MODEL_ID --repeats 5 --seed 17 --keep --output data/crowd-similar.jsonl
```

How to read experiment 1. `sf-hook` and `sf-expert` use the same hook, budget and
model, so they differ only in who selected the rules. That is what makes a difference
between them interpretable, and only for rows whose `delivery_check` is `ok` (the
intended rules arrived, byte-identical to the library). Exclude nothing: report rows
that failed the check separately.

| Result | What it suggests | What it does not settle |
|---|---|---|
| `sf-expert` wins, `sf-hook` loses | Selection is a strong suspect | Whether better retrieval alone would close the gap |
| Both lose to `none` or `native` | Something shared by both arms | Which of guidance, delivery, budget or task difficulty is responsible |
| `sf-hook` close to `sf-expert` | Retrieval is adequate on this task | Whether it holds on other tasks or a larger library |
| `native` matches `sf-expert` | Native loading delivers well at this library size | Whether it holds as the library grows |

When both lose, change one of those shared conditions at a time (a different budget,
different guidance for the same defect, a second task) before concluding anything.

A "similar" crowd contains skills that compete with the library for the same prompts
(other Postgres or React guidance), not just unrelated ones: unrelated distractors
alone can exaggerate or miss the real selection problem.

`--task` can be repeated to run a suite, and results are printed per task. Report
across distinct tasks. The four checks inside one task, or five repeats of it, are
not independent evidence. Five repeats are for debugging the experiment, not for
establishing a product advantage.

Report correctness, abstention (attempts that received no guidance), total cost and
latency together; the per-task summary prints all four. Offline, report rule precision
(relevant vs unnecessary), supporting rules and their cost, and prompts that received
no guidance, for ambiguous and explicitly mixed prompts alike.

The native arm has the same eligible module inventory but no authored SkillForge
core. It is the practical ordinary-skills comparator, not a pure composer ablation.

## Delivery evidence

`brief` is true when a `compose.py` tool result contained a brief header (skill arms),
or when the hook's own log shows it delivered a rule or the catalog (hook arms).
`hook_briefs`, `catalogs` and `rule_fetches` are recorded separately. A true `brief`
proves delivery, not that the model followed it. The hook log is kept outside the
project so the agent under test cannot read it. `--keep` copies it into the run folder.

## Inspect and report every attempt

1. Check result status and transcript before aggregating scores. A successful tool
   result with the brief header verifies output, not that the model followed it.
   Inspect `compose.jsonl` (kept runs) for ranked and actually delivered rule units.
2. Keep activation failures, grader timeouts and unknown-cost rows in the report.
   Do not replace unknown cost with zero. Summaries show their denominators.
3. Compare correctness first, then total billed cost, turns, cache usage and elapsed
   time. A smaller brief is not itself a cheaper end-to-end run. Preserve all raw
   per-run scores; the runner reports task passes separately from partial scores.
4. `--keep` saves project/transcript paths reported in JSONL. Its copied credential
   support directory is deleted even when retaining transcripts. Without `--keep`,
   raw transcripts are deleted but the JSONL attempt remains.
5. The JSONL file is an append-only local experiment record, not automatically an
   import into SQLite. Never suggest database promotion happened merely because
   `ab.py` completed.

## Feedback loop

Start by reading wrong-module and core-only cases in the saved routing predictions.
Have a reviewer author new positive, negative and ambiguous tasks before changing
the retriever. Record whether each task needs specialist instructions at all.
Reserve these cases as a holdout; do not use their answers as routing keywords.

For coding outcomes, build a separately versioned behavioral suite: concurrent
worker claims, no external payment call under a held lock, idempotent retry after
failure, cursor traversal without gaps/duplicates, and preserved legacy callers.
Include known-bad and known-good implementations, plus plausible wrong fixes, to
prove that the tests distinguish behavior. Static pattern checks can remain
secondary diagnostics. Do not silently replace the old suite and compare its scores.

After evaluating, classify failure as selection, delivery, instruction quality,
agent execution, or grader failure. Change one layer. If a scorer is defective,
version the correction and rerun every arm against it, or rescore retained outputs
for every arm while clearly labeling that analysis as retrospective.

Promote only a scoped claim supported by fresh tasks: improved quality for comparable
cost, or lower cost at comparable quality. Set acceptance thresholds before running.
If native still wins, do not manufacture a composite score that hides that result.
