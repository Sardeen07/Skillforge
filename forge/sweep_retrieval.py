#!/usr/bin/env python3
"""Parameter sweep for the retriever, over the development sets only.

  python forge/sweep_retrieval.py                 default grid, 2,400-token hook budget
  python forge/sweep_retrieval.py --json out.json

Never pass the held-out set here: tuning on it would turn it into a development set.
For each setting it reports recall@4 and pooled precision on the cases that need rules
(dev, mixed, security, performance), the abstention rate on the cases that need none
(negatives, ambiguous), and the mean estimated tokens spent on unnecessary rules. The
objective printed last is a simple F1 of recall and precision, gated on abstention,
so the chosen setting is the one that improves useful selection without buying it by
staying silent. Read the whole table, not only the winner.
"""
import argparse, itertools, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin/skills/skillforge/scripts'))
sys.path.insert(0, str(ROOT / 'forge'))
import retrieval  # noqa: E402
from score_retrieval import evaluate  # noqa: E402

POSITIVE = ('dev', 'mixed', 'security', 'performance', 'tasks')
NEGATIVE = ('negatives', 'ambiguous')


def load(name):
    path = ROOT / 'benchmarks/retrieval' / f'{name}.jsonl'
    return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]


def measure(index, budget):
    pos = [r for n in POSITIVE for r in evaluate(load(n), index, budget=budget)]
    neg = [r for n in NEGATIVE for r in evaluate(load(n), index, budget=budget)]
    rel = sum(r['relevant'] for r in pos)
    unn = sum(r['unnecessary'] for r in pos)
    recall = sum(r['score'] for r in pos) / len(pos)
    precision = rel / max(rel + unn, 1)
    abstain = sum(r['score'] == 1 for r in neg) / len(neg)
    waste = sum(r['unnecessary_tokens'] for r in pos + neg) / len(pos + neg)
    f1 = 2 * recall * precision / max(recall + precision, 1e-9)
    return dict(recall=recall, precision=precision, abstain=abstain, waste=waste, f1=f1,
                silent=sum(not r['picked'] for r in pos))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--budget', type=int, default=2400)
    ap.add_argument('--min-score', default='8,10,12,14')
    ap.add_argument('--relative', default='0.45,0.6,0.75')
    ap.add_argument('--matched', default='2')
    ap.add_argument('--brief-relative', default='0')
    ap.add_argument('--max-rules', default='0')
    ap.add_argument('--synonym-weight', default=None, help='e.g. 0,0.5 to ablate query expansion')
    ap.add_argument('--min-abstain', type=float, default=0.9, help='settings below this abstention rate are not chosen')
    ap.add_argument('--json')
    a = ap.parse_args()
    index = json.loads((ROOT / 'plugin/library/index.json').read_text(encoding='utf-8'))
    grid = itertools.product(map(float, a.min_score.split(',')), map(float, a.relative.split(',')),
                             map(int, a.matched.split(',')), map(float, a.brief_relative.split(',')),
                             map(int, a.max_rules.split(',')),
                             map(float, (a.synonym_weight or str(retrieval.SYNONYM_WEIGHT)).split(',')))
    rows = []
    print('| MIN_SCORE | RELATIVE | MIN_MATCHED | BRIEF_RELATIVE | MAX_RULES | recall@4 | precision | F1 | abstain | silent | waste tokens |')
    print('|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for ms, rel, mm, br, mr, sw in grid:
        retrieval.MIN_SCORE, retrieval.RELATIVE, retrieval.MIN_MATCHED = ms, rel, mm
        retrieval.BRIEF_RELATIVE, retrieval.MAX_RULES, retrieval.SYNONYM_WEIGHT = br, mr, sw
        m = measure(index, a.budget)
        rows.append(dict(min_score=ms, relative=rel, min_matched=mm, brief_relative=br, max_rules=mr,
                         synonym_weight=sw, **m))
        print(f"| {ms:g} | {rel:g} | {mm} | {br:g} | {mr} sw={sw:g} | {m['recall']:.1%} | {m['precision']:.1%} | {m['f1']:.3f} | "
              f"{m['abstain']:.1%} | {m['silent']} | {m['waste']:.0f} |", flush=True)
    ok = [r for r in rows if r['abstain'] >= a.min_abstain] or rows
    best = max(ok, key=lambda r: (round(r['f1'], 3), r['abstain']))
    print(f"\nbest (abstain >= {a.min_abstain:.0%}): MIN_SCORE={best['min_score']:g} RELATIVE={best['relative']:g} "
          f"MIN_MATCHED={best['min_matched']} BRIEF_RELATIVE={best['brief_relative']:g} MAX_RULES={best['max_rules']} "
          f"F1={best['f1']:.3f}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
