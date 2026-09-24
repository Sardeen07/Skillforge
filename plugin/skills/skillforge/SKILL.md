---
name: skillforge
description: Use for coding tasks that benefit from specialist debugging, testing, React performance, or Postgres guidance. Fetches curated rules from a local library, or specific rules by ID.
---

# SkillForge

If `# SkillForge brief:` or `# SkillForge catalog:` is already in context for this
prompt (an optional hook can inject it), use that instead of running the composer for
the same problem.

Otherwise, run the composer when the task has a concrete problem in these areas, and
again when you discover a new sub-problem (for example, reading the code shows a
transaction held across a network call):

1. Describe 1-4 concrete sub-tasks. Keep the user's symptoms, and name the technology
   when the project confirms it (it strongly steers retrieval).
2. `python3 "${CLAUDE_PLUGIN_ROOT}/skills/skillforge/scripts/compose.py" --subtask "<sub-task>" --stack "<stack>"`
   On Windows use a verified Python 3.10+ interpreter, often `python` or `py -3`.
   If the output does not start with `# SkillForge brief:`, it did not deliver guidance.
   Retry with a working interpreter and report failure honestly.
3. To read one rule named in a catalog: `compose.py --rule <module/name>` (repeatable).
   `compose.py --catalog` lists every rule. A step of a procedure arrives together
   with the earlier steps it depends on.
4. Apply rules only where they fit. The brief contains the complete rule text, so do
   not reopen those files. Respect the requested behavior; examples may omit
   application-specific requirements such as retries and idempotency. Provisional
   guidance has not demonstrated a quality win.
