#!/usr/bin/env python3
"""Materialize task specs into benchmarks/tasks/<name>/ and benchmarks/solutions/<name>/.

  python forge/taskgen/write.py tasks_2026_11_18        (a module in forge/taskgen/)

Each spec: category, task (prompt text), files (fixture), checks (grader body using the
harness's @check and load()), reference (correct files), variants (broken solutions as
text replacements on the reference). Validate afterwards with `npm run graders`.
"""
import importlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from harness import HARNESS, FOOTER  # noqa: E402

for modname in sys.argv[1:]:
    for name, t in importlib.import_module(modname).T.items():
        task, sol = ROOT / 'benchmarks/tasks' / name, ROOT / 'benchmarks/solutions' / name
        (sol / 'good').mkdir(parents=True, exist_ok=True)
        task.mkdir(parents=True, exist_ok=True)
        (task / 'task.txt').write_text(t['task'] + '\n', encoding='utf-8')
        for f, body in t['files'].items():
            (task / f).write_text(body, encoding='utf-8')
        (task / 'test.py').write_text(HARNESS + t['checks'].strip('\n') + '\n' + FOOTER, encoding='utf-8')
        for f, body in t['reference'].items():
            (sol / 'good' / f).write_text(body, encoding='utf-8')
        variants = [dict(name='good', expect='pass', why='reference solution')] + t['variants']
        (sol / 'variants.json').write_text(json.dumps(dict(task=name, reference='good', grader_version=1,
            category=t['category'], variants=variants), indent=2) + '\n', encoding='utf-8')
        print('wrote', name)
