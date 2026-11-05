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
import argparse, fnmatch, json, sys, time, math
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


def ndcg(needs, delivered, k):
    """NDCG@k over need groups; one rule can satisfy one previously unmet need."""
    if not needs:
        return 1.0 if not delivered else 0.0
    remaining = list(needs)
    dcg = 0.0
    for rank, rule in enumerate(delivered[:k], 1):
        hit = next((i for i, group in enumerate(remaining)
                    if any(fnmatch.fnmatch(rule, want) for want in group)), None)
        gain = 0.0
        if hit is not None:
            remaining.pop(hit)
            gain = 1.0
        dcg += gain / math.log2(rank + 1)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(k, len(needs)) + 1))
    return dcg / ideal if ideal else 0.0


def evaluate(cases, index, stack=(), baseline=False, k=4, budget=None):
    library = load_rules(index, ROOT / 'plugin/library')
    requires = {r['id']: r['requires'] for r in library}
    size = {r['id']: tokens(r['text']) for r in library}
    rows = []
    for c in cases:
        started = time.perf_counter()
        if baseline:
            selected = compose(index, c['mode'], [c['task']], stack=stack)[0]
            picked, rules, used = [m['name'] for m in selected if m['kind'] != 'core'], [], None
            precision = complete = None
            relevant_n = unnecessary_n = wasted = 0
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
            wasted = sum(size.get(i, 0) for i in ranked if not relevant(i, c.get('rules', [])))
            precision = relevant_n / len(ranked) if ranked else None
            have = {u['id'] for u in units}
            complete = all(set(requires.get(u['id'], [])) <= have for u in units)
        elapsed_ms = (time.perf_counter() - started) * 1000
        ndcg_k = ndcg(c.get('rules', []), rules, k) if not baseline else None
        precision_k = (sum(relevant(i, c.get('rules', [])) for i in rules) / min(k, len(rules))
                       if rules and not baseline else (0.0 if not baseline else None))
        module_hit = bool(set(picked) & set(c['expect'])) if c['expect'] else not picked
        score = (1.0 if not picked else 0.0) if not c['expect'] else (
            float(module_hit) if baseline else recall(c.get('rules', []), rules))
        rows.append(dict(task=c['task'], expected=c['expect'], needs=c.get('rules', []), picked=picked,
                         rules=rules, module_hit=module_hit, score=score, precision=precision,
                         precision_at_k=precision_k, ndcg_at_k=ndcg_k, retrieval_ms=elapsed_ms,
                         relevant=relevant_n, unnecessary=unnecessary_n, supporting=supporting,
                         supporting_tokens=sum(size.get(i, 0) for i in supporting),
                         dependencies_complete=complete, estimated_tokens=used, unnecessary_tokens=wasted))
    return rows


def check_labels(cases, ids, modules, where):
    """Every labeled rule pattern must match a rule and every expected module must exist.
    A pattern that matches nothing makes a case unscorable (it once hid a dev case for months)."""
    bad = []
    for n, c in enumerate(cases, 1):
        for need in c.get('rules', []):
            bad += [f'{where}:{n}: rule pattern {w!r} matches no rule' for w in need
                    if not any(fnmatch.fnmatch(i, w) for i in ids)]
        bad += [f'{where}:{n}: unknown module {m!r}' for m in c['expect'] if m not in modules]
    return bad


def report(rows, a, name, heldout=False):
    print(f'\n== {name}: {len(rows)} cases')
    for r in rows:
        if a.verbose or r['score'] < 1:
            got = r['picked'] if a.baseline else r['rules']
            print(f"{r['score']:.2f}  {r['task'][:90]} -> {got}")
    positive = [r for r in rows if r['expected']]
    negative = [r for r in rows if not r['expected']]
    mean = sum(r['score'] for r in rows) / len(rows)
    summary = {'set': name, 'cases': len(rows), 'mean_score': mean}
    if positive:
        label = 'module hit' if a.baseline else f'rule recall@{a.k}'
        rec = sum(r['score'] for r in positive) / len(positive)
        print(f"{label}: {rec:.1%} over {len(positive)} cases; "
              f"module hit {sum(r['module_hit'] for r in positive)}/{len(positive)}")
        summary.update(recall=rec, positives=len(positive))
        if not a.baseline:
            rel = sum(r['relevant'] for r in positive); unn = sum(r['unnecessary'] for r in positive)
            silent = sum(not r['picked'] for r in positive)
            print(f"selected rules: {rel} relevant, {unn} unnecessary (precision {rel / max(rel + unn, 1):.1%}); "
                  f"no guidance for {silent}/{len(positive)} prompts that needed some")
            ndcg_mean = sum(r['ndcg_at_k'] for r in positive) / len(positive)
            summary.update(precision=rel / max(rel + unn, 1), ndcg=ndcg_mean, silent=silent)
    if negative:
        abst = sum(r['score'] == 1 for r in negative)
        print(f"abstained {abst}/{len(negative)} cases that should get no rule")
        summary.update(abstained=abst, negatives=len(negative))
    if not a.baseline:
        ms = sorted(r['retrieval_ms'] for r in rows)
        p95 = ms[min(len(ms) - 1, int(0.95 * len(ms)))]
        print(f"mean precision@{a.k}: {sum(r['precision_at_k'] for r in rows) / len(rows):.1%}; "
              f"mean NDCG@{a.k} (cases needing rules): {summary.get('ndcg', 0):.3f}; "
              f"local runtime mean {sum(ms) / len(ms):.2f} ms, p95 {p95:.2f} ms")
        sup = [i for r in rows for i in r['supporting']]
        if sup:
            common = sorted(set(sup), key=lambda i: -sup.count(i))[:3]
            print(f"supporting rules: {len(sup)} included as dependencies, ~{sum(r['supporting_tokens'] for r in rows)} "
                  f"estimated tokens in total; most often {', '.join(f'{i} (x{sup.count(i)})' for i in common)}.")
        brief = sum(r['estimated_tokens'] for r in rows) / len(rows)
        waste = sum(r['unnecessary_tokens'] for r in rows) / len(rows)
        print(f"dependencies complete in {sum(bool(r['dependencies_complete']) for r in rows)}/{len(rows)} briefs; "
              f"mean brief ~{brief:.0f} estimated tokens, of which ~{waste:.0f} are unnecessary rules")
        summary.update(mean_brief_tokens=brief, mean_unnecessary_tokens=waste, p95_ms=p95)
    note = ('Held-out: report once per retriever version; do not tune on misses.' if heldout
            else 'Development routing only; these cases were seen while tuning.')
    print(f'mean case score {mean:.1%}. {note}')
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cases', action='append', help='a JSONL case file; repeatable (default: dev set)')
    ap.add_argument('--suite', action='store_true', help='every development set in benchmarks/retrieval/')
    ap.add_argument('--heldout', action='store_true', help='the frozen held-out set (benchmarks/heldout/cases.jsonl)')
    ap.add_argument('--stack', default='')
    ap.add_argument('--baseline', action='store_true')
    ap.add_argument('--k', type=int, default=4)
    ap.add_argument('--budget', type=int, help='brief budget in estimated tokens (default: the mode budget)')
    ap.add_argument('--min', type=float, dest='floor', help='fail if any set\'s mean case score is below this')
    ap.add_argument('--json')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    index = json.loads((ROOT / 'plugin/library/index.json').read_text(encoding='utf-8'))
    files = list(a.cases or [])
    if a.suite:
        files += sorted(str(p) for p in (ROOT / 'benchmarks/retrieval').glob('*.jsonl'))
    if a.heldout:
        files.append(str(ROOT / 'benchmarks/heldout/cases.jsonl'))
    files = files or [str(ROOT / 'benchmarks/retrieval/dev.jsonl')]
    library = load_rules(index, ROOT / 'plugin/library')
    ids = {r['id'] for r in library}
    modules = {r['module'] for r in library}
    stack = tuple(filter(None, a.stack.split(',')))
    summaries, all_rows, failed = [], {}, []
    for f in files:
        cases = [json.loads(l) for l in Path(f).read_text(encoding='utf-8').splitlines() if l.strip()]
        if not cases: ap.error(f'{f}: cases must not be empty')
        bad = check_labels(cases, ids, modules, Path(f).name)
        if bad:
            sys.exit('invalid labels:\n' + '\n'.join(bad))
        rows = evaluate(cases, index, stack, a.baseline, a.k, a.budget)
        s = report(rows, a, Path(f).stem, heldout='heldout' in str(f))
        summaries.append(s)
        all_rows[Path(f).stem] = rows
        if a.floor is not None and s['mean_score'] < a.floor:
            failed.append(f"{s['set']}: {s['mean_score']:.1%} < {a.floor:.1%}")
    if len(summaries) > 1:
        print('\n| set | cases | recall@%d | precision | NDCG@%d | abstained | mean brief (est. tokens) | unnecessary tokens |' % (a.k, a.k))
        print('|---|---:|---:|---:|---:|---:|---:|---:|')
        for s in summaries:
            pct = lambda key: f"{s[key]:.1%}" if key in s else '-'
            ab = f"{s['abstained']}/{s['negatives']}" if 'negatives' in s else '-'
            nd = f"{s['ndcg']:.3f}" if 'ndcg' in s else '-'
            print(f"| {s['set']} | {s['cases']} | {pct('recall')} | {pct('precision')} | {nd} | {ab} | "
                  f"{s.get('mean_brief_tokens', 0):.0f} | {s.get('mean_unnecessary_tokens', 0):.0f} |")
    if a.json:
        Path(a.json).write_text(json.dumps({'summaries': summaries, 'rows': all_rows}, indent=2) + '\n', encoding='utf-8')
    if failed:
        sys.exit('retrieval floor: ' + '; '.join(failed))


if __name__ == '__main__': main()
