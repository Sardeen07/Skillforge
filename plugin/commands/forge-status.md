---
description: Show what the most recent SkillForge brief delivered, and why
---
Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/skillforge/scripts/compose.py" --status`
(on Windows use a working Python 3.10+, often `python`). Report its output: for each part
of the prompt, which rules matched and their scores (or that it abstained), then which
units were delivered, skipped as already delivered this session, or dropped for budget.
