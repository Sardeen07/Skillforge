# Adding to the library

## Add an authored rule

1. Open the module's `plugin/library/modules/<module>/RULES.md` (or create a new module
   folder with a `RULES.md` whose frontmatter has `module`, `capability`, `technologies`,
   `applies`, `checked_against`, `authorship`, `review`).
2. Add an entry:

   ```md
   ## short-kebab-id: Imperative title that states the guidance
   tags: technology, concept, symptom words, at least three
   keywords: phrases a developer would type when they have this problem
   refs: https://official.docs.example/page-the-rule-was-checked-against

   Two to five sentences of specific, actionable guidance: what to do, what not to do,
   and why. A short code example when it removes ambiguity.
   ```

   Optional lines: `technologies:` (overrides the module's), `requires:` / `conflicts:`
   (rule ids in this module, or `module/id`), `versions:` (e.g. `python>=3.11`).
3. A rule earns its place only if it is specific enough to change a coding decision. Do not
   add generic advice ("write clean code"), and do not paraphrase copyrighted text.
4. If the module is new, register it in `forge/curation/coding.json`
   (`{"name": "...", "source": {"kind": "authored", "license": "MIT"}, "status": "provisional"}`).
5. Rebuild and check:

   ```sh
   node forge/py.mjs forge/sf.py migrate
   node forge/py.mjs forge/sf.py import forge/curation/coding.json
   node forge/py.mjs forge/sf.py export
   npm run validate:library -- --verify-links
   npm test
   npm run retrieval:suite      # must not get worse; add dev cases for the new rules
   ```

New rules stay `evidence: untested`. Only a controlled comparison (see
[BENCHMARK_PROTOCOL.md](BENCHMARK_PROTOCOL.md)) may change that.

## Import an upstream skill

1. Scan it: `npm run scan -- owner/repo` (license, injection, hidden characters, bundled
   scripts, overlap with the library). Only `accept` verdicts with MIT, Apache-2.0, BSD,
   ISC, CC0 or Unlicense licenses are eligible; copyleft and unlicensed content is not.
2. Add a curation entry with the repository, the **exact commit**, the path, the license,
   `technologies` (canonical names from `technologies.json`) and `status: candidate`.
3. `sf.py import` copies the files at that commit with `SOURCE.json` and the upstream
   LICENSE; `export` leaves candidates out of retrieval.
4. A person reads every rule, then promotes it to `provisional` and runs the checks above.

## Add a technology

Add it to `plugin/library/technologies.json`. Put words that unambiguously name it in
`aliases`, words that merely suggest it in `hints`, and never a common English word as an
alias (`go`, `express`, `node`, `rails` are hints or only appear inside phrases). Add
package names and marker files for manifest detection, and a test in `tests/test_v1.py`.

## Add a benchmark case or task

- Retrieval cases: one JSON object per line in `benchmarks/retrieval/<set>.jsonl`; labels
  must name existing rules (the scorecard refuses dead patterns). Never edit
  `benchmarks/heldout/cases.jsonl`; it is frozen by hash.
- Coding tasks: see [benchmarks/tasks/README.md](../benchmarks/tasks/README.md). A task
  needs a symptom-phrased `task.txt`, a hidden behavioral `test.py`, a reference solution
  and broken variants under `benchmarks/solutions/<task>/`, validated by `npm run graders`.
