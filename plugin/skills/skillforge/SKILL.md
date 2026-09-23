---
name: skillforge
description: Use for coding tasks that benefit from specialist debugging, testing, React performance, or Postgres guidance. Selects provisional instructions from a local library.
---

# SkillForge

1. For substantial coding work, identify 1-4 concrete sub-tasks. Preserve the user's
   symptoms and name the technology only when the project confirms it. Skip the
   composer for trivial wording or formatting changes.
2. Run once with repeated `--subtask` arguments and an optional known stack:
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/skillforge/scripts/compose.py" --mode coding --subtask "<sub-task>" --stack "<stack>"`
   On Windows use a verified Python 3.10+ interpreter, often `python` or `py -3`.
   If the output does not start with `# SkillForge brief:`, the command did not
   deliver guidance. Retry with a working interpreter and report failure honestly.
3. Apply the relevant instructions in the brief. Rule delivery includes complete
   selected reference text, so do not reopen those files. When a full module index
   names reference files, read the named rules. Respect the requested behavior;
   examples may omit application-specific requirements such as retries and
   payment idempotency. Provisional guidance has not demonstrated a quality win.
4. Run again only for new sub-tasks. Caching is off by default. To reuse instructions
   within this conversation, explicitly pass `--session "<unique-session-file>"`
   every time. Never share the file across conversations or concurrent agents.
   Add `--reset` after context compaction. Otherwise omit `--session`.
