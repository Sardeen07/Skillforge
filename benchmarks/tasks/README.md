# Benchmark tasks

One folder per task repo, each with a hidden `test.py` that `forge/ab.py` copies in
*after* the agent has finished. The agent never sees it.

| Task | Checks | Use |
|---|---|---|
| `pg-queue-throughput` | 4 | The discriminating task. Every defect has a plausible wrong fix. |
| `react-waterfall` | 3 | End-to-end smoke test. All arms now solve it; keep it, don't draw conclusions from it. |
| `binary-search` | 1 | Harness smoke test only. Solved in three tool calls with no skills. |

## What makes a task worth benchmarking

A task discriminates only when the model's *default* answer is wrong. If Claude
already knows the fix, every arm scores full marks and the arm with the smallest
prompt wins on cost — which measures prompt size, not skill quality.

`pg-queue-throughput` is built to that rule:

| Check | The obvious answer | Why it is wrong |
|---|---|---|
| `skip-locked` | "add `for update`" | it is already there; workers need `skip locked` |
| `short-transaction` | "wrap it in a transaction" | the transaction is the problem — it spans a 2-5s HTTP call |
| `keyset-pagination` | "add an index for the order by" | `offset` still scans and discards every skipped row |
| `fk-index` | "Postgres indexes the foreign key" | it does not; only primary keys |

## Three rules a task must satisfy

Rule 1 is enforced by `BenchmarkTasks` in `tests/`. Rules 2 and 3 need a human.

1. **The test must fail on the unfixed fixture.** Otherwise it measures nothing.
2. **The test must be passable.** Check this by hand before trusting a number.
   `react-waterfall` originally shipped without a `components/` directory, so its
   barrel-import check asked the agent to invent an unverifiable path. Every arm
   scored 2/3 and the ceiling looked like a tie between the arms.
3. **The fixture must not argue for its own defect.** `pg-queue-throughput` shipped
   with this comment on the payment call:

   > `# Charge the customer before releasing the job, so a crash can never leave a`
   > `# job marked done without a receipt.`

   The agent read it, weighed it, and refused the fix — correctly, on the information
   the fixture gave it:

   > "I kept the charge inside the transaction on purpose. Moving it outside would
   > change what happens if a worker crashes."

   A fixture states the situation; it never defends the bug. Where the objection is
   real, the fixture must answer it — here by documenting the reaper in `ops/reaper.md`
   that already requeues stalled jobs — so the intended fix is unambiguously correct.

Write the reference solution before you trust the task. All three failures above were
found that way, and each one had silently flattened a benchmark.

## Adding a task

```
benchmarks/tasks/<name>/
  task.txt      the prompt, phrased as a person would report the symptom
  test.py       hidden; prints "SCORE: n/m" and exits 0 only on a full score
  <fixture>     source files, subdirectories included
```

Phrase `task.txt` by symptom, never by remedy — naming the fix hands every arm the
answer and collapses the difference you are trying to measure.

Prefer AST or parser checks over regex where a regex would be fooled by control flow.
The `short-transaction` check walks statements precisely because the fixture commits
early on one branch, and a positional "between BEGIN and COMMIT" regex called that a pass.
