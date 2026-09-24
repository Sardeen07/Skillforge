#!/usr/bin/env python3
"""Check that each task's hidden grader passes correct solutions and fails broken ones.

Solutions live in benchmarks/solutions/<task>/, outside the task folder, so an agent
under test never sees them and the grader never reads their files. Each variant is
the task fixture, overlaid with the reference solution, with explicit text
replacements applied.

A correct variant (expect: pass) must score full marks. A broken variant must fail every
check in must_fail and pass every check in must_pass; failing other checks too can be
legitimate and is reported, not rejected. Graders with more than one mode (behavioral
with a database, static without) are validated in each mode that can run here.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / 'benchmarks/tasks'
SOLUTIONS = ROOT / 'benchmarks/solutions'
SCORE = re.compile(r'SCORE:\s*(\d+)\s*/\s*(\d+)')


def build(task, spec, reference, dest):
    shutil.copytree(TASKS / task, dest, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(reference, dest, dirs_exist_ok=True)
    for name, edits in spec.get('replace', {}).items():
        path = dest / name
        text = path.read_text(encoding='utf-8')
        for old, new in edits:
            if old not in text:
                raise ValueError(f"{spec['name']}: {name} does not contain {old[:50]!r}")
            text = text.replace(old, new, 1)
        path.write_text(text, encoding='utf-8')


def grade(folder, mode=None):
    env = {**os.environ, **({'GRADER_MODE': mode} if mode else {})}
    r = subprocess.run([sys.executable, 'test.py'], cwd=folder, capture_output=True, text=True,
                       encoding='utf-8', timeout=300, env=env)
    m = SCORE.search(r.stdout)
    header = re.search(r'^GRADER: (.+)$', r.stdout, re.M)
    return dict(score=f'{m[1]}/{m[2]}' if m else None, full=bool(m) and m[1] == m[2],
                failed=re.findall(r'^FAIL\s+(\S+)', r.stdout, re.M),
                passed=re.findall(r'^PASS\s+(\S+)', r.stdout, re.M),
                grader=header[1] if header else 'unknown', output=r.stdout + r.stderr)


def judge(spec, result):
    """(ok, problems, extra failures) for one variant's grading result."""
    if result['score'] is None:
        return False, ['grader printed no SCORE'], []
    if spec.get('expect') == 'pass':
        return result['full'], ([] if result['full'] else [f"correct solution failed {result['failed']}"]), []
    problems = [f'should fail {c}' for c in spec.get('must_fail', []) if c not in result['failed']]
    problems += [f'should pass {c}' for c in spec.get('must_pass', []) if c not in result['passed']]
    if result['full']:
        problems.append('broken solution got full marks')
    extra = [c for c in result['failed'] if c not in spec.get('must_fail', [])]
    return not problems, problems, extra


def validate(task, modes=(None,)):
    cfg = json.loads((SOLUTIONS / task / 'variants.json').read_text(encoding='utf-8'))
    reference = SOLUTIONS / task / cfg['reference']
    rows = []
    for spec in cfg['variants']:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / task
            build(task, spec, reference, dest)
            for mode in modes:
                result = grade(dest, mode)
                ok, problems, extra = judge(spec, result)
                rows.append(dict(task=task, variant=spec['name'], mode=result['grader'], ok=ok,
                                 problems=problems, extra_failures=extra, score=result['score']))
                shutil.rmtree(dest / '__pycache__', ignore_errors=True)
    return rows


def behavioral_available():
    try:
        import pgserver, psycopg  # noqa: F401
        return True
    except ImportError:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--task', action='append', help='default: every task')
    ap.add_argument('--static-only', action='store_true', help='skip the behavioral mode')
    a = ap.parse_args()
    tasks = a.task or sorted(p.name for p in TASKS.iterdir() if p.is_dir())
    modes = ['static'] + ([] if a.static_only or not behavioral_available() else [None])
    if None not in modes:
        print('NOTE: behavioral grading is unavailable here (pip install -r requirements-dev.txt); '
              'validating static mode only.')
    bad = False
    for task in tasks:
        if not (SOLUTIONS / task / 'variants.json').exists():
            print(f'{task}: NOT VALIDATED (no reference or broken solutions yet)')
            continue
        for r in validate(task, modes):
            status = 'ok' if r['ok'] else 'WRONG: ' + '; '.join(r['problems'])
            extra = f"  (also fails {', '.join(r['extra_failures'])})" if r['extra_failures'] else ''
            print(f"{task}/{r['variant']:30} [{r['mode']}] {r['score']}  {status}{extra}")
            bad |= not r['ok']
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
