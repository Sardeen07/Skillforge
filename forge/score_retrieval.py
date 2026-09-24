#!/usr/bin/env python3
"""Offline routing scorecard, not task-success evidence.

Scores what the brief actually delivers, at the rule level. Each case lists the
rules it needs; each need is a list of acceptable rule IDs (fnmatch patterns allowed).
A case scores the share of its needs met by the first --k delivered rules (recall@k).
A case with no expected module must abstain: it scores 1 only if no rule is delivered.

Recall alone rewards delivering more, so every delivered rule is also classified:
  relevant     selected by ranking and meets a labeled need
  unnecessary  selected by ranking and meets no labeled need
  supporting   not selected itself; included because a selected rule declares it requires it
Precision is relevant / (relevant + unnecessary). Supporting rules are reported with
their token cost rather than excused: each declared dependency should earn its place.
The report also counts prompts that needed guidance and received none, since
precision among delivered rules cannot reveal excessive abstention.

--baseline scores the original keyword module selector, at module level only.
"""
import argparse, fnmatch, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin/skills/skillforge/scripts'))
from compose import compose
from delivery import build_brief
from retrieval import load_rules, tokens


def recall(needs, delivered):
    if not needs:
        return None
    met = sum(any(fnmatch.fnmatch(d, want) for d in delivered for want in need) for need in needs)
    return met / len(needs)


def relevant(rule, needs):
    return any(fnmatch.fnmatch(rule, want) for need in needs for want in need)


def evaluate(cases, index, stack=(), baseline=False, k=4, budget=None):
    library = load_rules(index, ROOT / 'plugin/library')
    requires = {r['id']: r['requires'] for r in library}
    size = {r['id']: tokens(r['text']) for r in library}
    rows = []
    for c in cases:
        if baseline:
            selected = compose(index, c['mode'], [c['task']], stack=stack)[0]
            picked, rules, used = [m['name'] for m in selected if m['kind'] != 'core'], [], None
            precision = complete = None
            relevant_n = unnecessary_n = 0
            supporting = []
        else:
            _, _, log = build_brief(index, ROOT / 'plugin/library', c['mode'], [c['task']], stack=stack,
                                    budget=budget, split=True)
            units = [u for u in log['units'][1:] if u['result'] == 'delivered']
            ranked = [u['id'] for u in units if not u['required_by']]
            rules = ranked[:k]
            picked = sorted({u['module'] for u in units})
            used = log['estimated_output_tokens']
            relevant_n = sum(relevant(r, c.get('rules', [])) for r in ranked)
            unnecessary_n = len(ranked) - relevant_n
            supporting = [u['id'] for u in units if u['required_by']]
            precision = relevant_n / len(ranked) if ranked else None
            have = {u['id'] for u in units}
            complete = all(set(requires.get(u['id'], [])) <= have for u in units)
        module_hit = bool(set(picked) & set(c['expect'])) if c['expect'] else not picked
        score = (1.0 if not picked else 0.0) if not c['expect'] else (
            float(module_hit) if baseline else recall(c.get('rules', []), rules))
        rows.append(dict(task=c['task'], expected=c['expect'], needs=c.get('rules', []), picked=picked,
                         rules=rules, module_hit=module_hit, score=score, precision=precision,
                         relevant=relevant_n, unnecessary=unnecessary_n, supporting=supporting,
                         supporting_tokens=sum(size.get(i, 0) for i in supporting),
                         dependencies_complete=complete, estimated_tokens=used))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cases', default=str(ROOT / 'benchmarks/retrieval.jsonl'))
    ap.add_argument('--stack', default='')
    ap.add_argument('--baseline', action='store_true')
    ap.add_argument('--k', type=int, default=4)
    ap.add_argument('--budget', type=int, help='brief budget in estimated tokens (default: the mode budget)')
    ap.add_argument('--min', type=float, dest='floor', help='fail below this mean case score')
    ap.add_argument('--json')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    index = json.loads((ROOT / 'plugin/library/index.json').read_text(encoding='utf-8'))
    cases = [json.loads(l) for l in Path(a.cases).read_text(encoding='utf-8').splitlines() if l.strip()]
    if not cases: ap.error('cases must not be empty')
    rows = evaluate(cases, index, tuple(filter(None, a.stack.split(','))), a.baseline, a.k, a.budget)
    for r in rows:
        if a.verbose or r['score'] < 1:
            got = r['picked'] if a.baseline else r['rules']
            print(f"{r['score']:.2f}  {r['task'][:90]} -> {got}")
    positive = [r for r in rows if r['expected']]
    negative = [r for r in rows if not r['expected']]
    mean = sum(r['score'] for r in rows) / len(rows)
    if positive:
        label = 'module hit' if a.baseline else f'rule recall@{a.k}'
        print(f"{label}: {sum(r['score'] for r in positive) / len(positive):.1%} over {len(positive)} cases; "
              f"module hit {sum(r['module_hit'] for r in positive)}/{len(positive)}")
        if not a.baseline:
            rel = sum(r['relevant'] for r in positive); unn = sum(r['unnecessary'] for r in positive)
            print(f"selected rules: {rel} relevant, {unn} unnecessary (precision {rel / max(rel + unn, 1):.1%}); "
                  f"no guidance for {sum(not r['picked'] for r in positive)}/{len(positive)} prompts that needed some")
    if negative:
        print(f"abstained {sum(r['score'] == 1 for r in negative)}/{len(negative)} unrelated tasks")
    if not a.baseline:
        sup = [i for r in rows for i in r['supporting']]
        if sup:
            common = sorted(set(sup), key=lambda i: -sup.count(i))[:3]
            print(f"supporting rules: {len(sup)} included as dependencies, ~{sum(r['supporting_tokens'] for r in rows)} "
                  f"estimated tokens in total; most often {', '.join(f'{i} (x{sup.count(i)})' for i in common)}. "
                  "Review that each is truly needed.")
        else:
            print('supporting rules: none included')
        print(f"dependencies complete in {sum(bool(r['dependencies_complete']) for r in rows)}/{len(rows)} briefs; "
              f"mean brief ~{sum(r['estimated_tokens'] for r in rows) / len(rows):.0f} estimated tokens")
    print(f'mean case score {mean:.1%}. Development routing only; these cases were seen while tuning.')
    if a.json: Path(a.json).write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    if a.floor is not None and mean < a.floor: sys.exit(f'retrieval floor: {mean:.1%} < {a.floor:.1%}')


if __name__ == '__main__': main()
