#!/usr/bin/env python3
"""Offline development routing scorecard, not task-success evidence."""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin/skills/skillforge/scripts'))
from compose import compose
from delivery import build_brief


def evaluate(cases, index, stack=(), baseline=False):
    rows = []
    for c in cases:
        if baseline:
            selected, used, _, _ = compose(index, c['mode'], [c['task']], stack=stack)
            picked = [m['name'] for m in selected if m['kind'] != 'core']
        else:
            _, _, log = build_brief(index, ROOT / 'plugin/library', c['mode'], [c['task']], stack=stack)
            picked = [n for n in log['delivered_modules'] if n != index['modes'][c['mode']]['core']]
            used = log['estimated_output_tokens']
        ok = bool(set(picked) & set(c['expect'])) if c['expect'] else not picked
        rows.append(dict(task=c['task'], expected=c['expect'], picked=picked, hit=ok, estimated_tokens=used))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases', default=str(ROOT / 'benchmarks/retrieval.jsonl'))
    ap.add_argument('--stack', default='')
    ap.add_argument('--baseline', action='store_true')
    ap.add_argument('--min', type=float, dest='floor')
    ap.add_argument('--json')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    index = json.loads((ROOT / 'plugin/library/index.json').read_text(encoding='utf-8'))
    cases = [json.loads(l) for l in Path(a.cases).read_text(encoding='utf-8').splitlines() if l.strip()]
    if not cases: ap.error('cases must not be empty')
    rows = evaluate(cases, index, tuple(filter(None, a.stack.split(','))), a.baseline)
    for r in rows:
        if a.verbose or not r['hit']:
            print(f"{'hit' if r['hit'] else 'miss'}  {r['task']} -> {r['picked']} expected {r['expected']}")
    hits = sum(r['hit'] for r in rows); rate = hits / len(rows)
    print(f"hit {hits}/{len(rows)} ({rate:.1%}); core-only {sum(not r['picked'] for r in rows)}/{len(rows)}")
    print('Development routing only. Baseline estimates exclude wrappers and subsequent rule reads.')
    if a.json: Path(a.json).write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    if a.floor is not None and rate < a.floor: sys.exit(f'retrieval floor: {rate:.1%} < {a.floor:.1%}')


if __name__ == '__main__': main()
