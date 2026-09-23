---
name: skillforge
description: Use at the start of any multi-step task (coding, debugging, testing, writing, research) to load only the benchmarked skill instructions that task needs.
---

# SkillForge

1. Pick a mode: coding, debugging, testing, writing, or research.
2. Break the task into 2-5 short sub-task labels (e.g. "reproduce bug", "write test", "patch auth").
3. Run:
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/skillforge/scripts/compose.py --mode <mode> "<sub-task labels>"`
4. Follow the brief it prints. Do not read library/ files yourself; the script already chose them.
5. If the brief recommends an external plugin that isn't installed, tell the user once and continue.
