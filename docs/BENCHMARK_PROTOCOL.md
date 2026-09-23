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
npm run retrieval -- --min 0.60
npm run ab -- --dry-run --arms none,native,skillforge,sf-modules,sf-keywords
```

## Separate interventions

Run these on fresh task copies, with a new output file for each experiment:

```sh
# Does direct delivery help, with the same retrieval and module selection?
npm run ab -- --task benchmarks/tasks/pg-queue-throughput --arms sf-modules,skillforge --model YOUR_MODEL_ID --repeats 5 --seed 17 --keep --output data/delivery-ab.jsonl

# Does reference routing help, with the same delivery implementation?
npm run ab -- --task benchmarks/tasks/pg-queue-throughput --arms sf-keywords,skillforge --model YOUR_MODEL_ID --repeats 5 --seed 17 --keep --output data/routing-ab.jsonl

# Does the complete tool justify itself against real alternatives?
npm run ab -- --task benchmarks/tasks/pg-queue-throughput --arms none,native,skillforge --model YOUR_MODEL_ID --repeats 5 --seed 17 --keep --output data/product-ab.jsonl
```

Five repeats are a diagnostic starting point, not adequate evidence for small
statistical differences. Extend to multiple independent tasks before making a
product claim. Repeats on one task do not become independent task coverage.

`sf-keywords` is a routing ablation, not a byte-identical historical baseline.
`sf-modules` is a delivery ablation, not the old plugin. Both use the new session,
budget and runner controls. Module selection is shared across delivery arms before
payload budget enforcement; different-sized payloads can lead to different actual
coverage under the same budget. That is part of the delivery intervention.

The native arm has the same eligible module inventory but no authored SkillForge
core. It is the practical ordinary-skills comparator, not a pure composer ablation.

## Inspect and report every attempt

1. Check result status and transcript before aggregating scores. A successful tool
   result with the brief header verifies output, not that the model followed it.
   Inspect `compose.jsonl` for selected and actually delivered rule units.
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
