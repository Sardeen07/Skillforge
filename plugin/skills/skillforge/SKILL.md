---
name: skillforge
description: Use at the start of any coding task (features, bugs, tests, React, databases) to load a small coding core plus only the vetted instruction modules this task needs.
---

# SkillForge

1. Split the task into 1-4 short sub-tasks (e.g. "find why the list rerenders", "fix the bug", "add an index").
2. Note the project stack if obvious (e.g. react, postgres).
3. Run, with one --subtask per sub-task:
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/skillforge/scripts/compose.py --mode coding --session /tmp/skillforge-session.json --subtask "<sub-task>" --stack <stack>`
4. Follow the brief it prints. Do not browse library/ yourself; open a module's reference files only if the brief points you there and you need them.
5. If new sub-tasks appear later, run it again with the new sub-tasks. After context is compacted, add --reset so earlier modules are re-emitted.
