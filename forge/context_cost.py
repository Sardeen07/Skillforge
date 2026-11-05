#!/usr/bin/env python3
"""Offline comparison of the context each delivery arm adds to a session. No model calls.

  python forge/context_cost.py                               the 28 behavioral task prompts
  python forge/context_cost.py --cases benchmarks/retrieval/dev.jsonl
  python forge/context_cost.py --price-per-mtok 3.00         also print $ per 1,000 sessions

What this measures: estimated tokens (characters / 4) of the guidance text each arm puts in
context for a prompt, and whether the labeled rules for that prompt are in it. What it does
NOT measure: what the model actually reads, output tokens, cache hits, the number of
requests, tool-call overhead, or whether the code got better. Those need paid runs with
forge/ab.py. Use this to see the size of the context bill each arm starts with, not to
claim savings.

Arms (same names as forge/ab.py):
  none        nothing.
  native      every module installed as a skill: the skill listing (name + description) is
              always in context; this assumes the model then loads exactly the modules that
              hold the labeled rules (a best case for native selection), plus the labeled
              reference files of imported modules, which their SKILL.md tells it to read.
  skillforge  the SkillForge skill's listing, plus one brief for the prompt if the model
              chooses to call it (assumed: called once, with the raw prompt).
  sf-hook     the brief the hook injects for the raw prompt (empty when it abstains).
  sf-catalog  the hook's bounded catalog, plus the labeled rules fetched by ID (best case).
  sf-expert   exactly the labeled rules (the first acceptable rule of each need), as the
              fixed-selection hook delivers them.
"""
import argparse, fnmatch, json, re, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'plugin/library'
sys.path.insert(0, str(ROOT / 'plugin/skills/skillforge/scripts'))
from delivery import build_brief, catalog_text, get_rules, library  # noqa: E402
from retrieval import strip_frontmatter, tokens  # noqa: E402

HOOK_BUDGET = 2400
FETCH = 'python compose.py'


def skill_listing_line(name, description):
    return f'- {name}: {description}\n'


def native_listing(index):
    """What Claude Code lists for every installed skill: name and description."""
    sys.path.insert(0, str(ROOT / 'forge'))
    from ab import native_skill_text
    lines = []
    for m in index['modules']:
        if m['kind'] != 'module' or m['status'] not in ('provisional', 'preferred'):
            continue
        text = (LIB / m['path']).read_text(encoding='utf-8')
        if m['path'].endswith('RULES.md'):
            text = native_skill_text(m, text)
        fields, _ = strip_frontmatter(text)
        lines.append(skill_listing_line(fields.get('name', m['name']), fields.get('description', '').strip('"')))
    return ''.join(lines)


def native_body(index, module):
    m = next(x for x in index['modules'] if x['name'] == module)
    text = (LIB / m['path']).read_text(encoding='utf-8')
    if m['path'].endswith('RULES.md'):
        sys.path.insert(0, str(ROOT / 'forge'))
        from ab import native_skill_text
        text = native_skill_text(m, text)
    return text


def labeled_ids(case, ids):
    """The first concrete rule ID that satisfies each need (what an expert would hand over)."""
    out = []
    for need in case.get('rules', []):
        for want in need:
            hit = next((i for i in sorted(ids) if fnmatch.fnmatch(i, want)), None)
            if hit:
                out.append(hit)
                break
    return list(dict.fromkeys(out))


def covered(text_ids, case):
    needs = case.get('rules', [])
    if not needs:
        return None
    return sum(any(fnmatch.fnmatch(i, w) for i in text_ids for w in need) for need in needs) / len(needs)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cases', default=str(ROOT / 'benchmarks/retrieval/tasks.jsonl'))
    ap.add_argument('--price-per-mtok', type=float, help='input price in $ per million tokens, for a $ estimate')
    ap.add_argument('--json')
    a = ap.parse_args()
    index = json.loads((LIB / 'index.json').read_text(encoding='utf-8'))
    _, rules = library(index, LIB, 'coding')
    by_id = {r['id']: r for r in rules}
    cases = [json.loads(l) for l in Path(a.cases).read_text(encoding='utf-8').splitlines() if l.strip()]

    listing_native = native_listing(index)
    skill = (ROOT / 'plugin/skills/skillforge/SKILL.md').read_text(encoding='utf-8')
    sf_fields, _ = strip_frontmatter(skill)
    listing_sf = skill_listing_line('skillforge', sf_fields.get('description', ''))
    catalog = catalog_text(index, LIB, 'coding', FETCH, budget=HOOK_BUDGET)

    arms = {k: [] for k in ('none', 'native', 'skillforge', 'sf-hook', 'sf-catalog', 'sf-expert')}
    cover = {k: [] for k in arms}
    for c in cases:
        want = labeled_ids(c, by_id)
        brief, _, log = build_brief(index, LIB, 'coding', [c['task']], budget=HOOK_BUDGET, split=True, abstain_empty=True)
        delivered = [u['id'] for u in log['units'][1:] if u['result'] == 'delivered']
        modules = list(dict.fromkeys(i.split('/')[0] for i in want))
        refs = ''.join(by_id[i].get('delivery', by_id[i]['text']) for i in want
                       if not by_id[i]['path'].endswith(('RULES.md', 'MODULE.md')) and '#' not in by_id[i]['path'])
        native = listing_native + ''.join(native_body(index, m) for m in modules) + refs
        fetched, _ = get_rules(index, LIB, 'coding', want) if want else ('', [])
        expert, _, _ = build_brief(index, LIB, 'coding', [], budget=50_000, rule_ids=want) if want else ('', set(), {})
        sizes = {'none': 0, 'native': tokens(native), 'skillforge': tokens(listing_sf) + tokens(brief),
                 'sf-hook': tokens(brief), 'sf-catalog': tokens(catalog) + tokens(fetched), 'sf-expert': tokens(expert)}
        got = {'none': [], 'native': want, 'skillforge': delivered, 'sf-hook': delivered,
               'sf-catalog': want, 'sf-expert': want}
        for arm in arms:
            arms[arm].append(sizes[arm])
            cv = covered(got[arm], c)
            if cv is not None:
                cover[arm].append(cv)

    print(f'{len(cases)} prompts from {Path(a.cases).name}. Estimated tokens (chars / 4) of guidance added to context.')
    print(f'Native skill listing alone: ~{tokens(listing_native)} tokens for '
          f"{sum(1 for m in index['modules'] if m['kind'] == 'module')} modules; SkillForge skill listing: ~{tokens(listing_sf)}.")
    print('Assumptions per arm are in this script\'s docstring; native and sf-catalog assume perfect selection.\n')
    head = '| arm | mean added tokens | median | max | labeled needs covered |'
    if a.price_per_mtok:
        head += f' $ per 1,000 sessions at ${a.price_per_mtok:g}/MTok (uncached) |'
    print(head)
    print('|---|---:|---:|---:|---:|' + ('---:|' if a.price_per_mtok else ''))
    summary = {}
    for arm, xs in arms.items():
        cv = statistics.mean(cover[arm]) if cover[arm] else 0.0
        row = f'| {arm} | {statistics.mean(xs):.0f} | {statistics.median(xs):.0f} | {max(xs)} | {cv:.0%} |'
        if a.price_per_mtok:
            row += f' {statistics.mean(xs) * 1000 * a.price_per_mtok / 1e6:.2f} |'
        print(row)
        summary[arm] = dict(mean_tokens=statistics.mean(xs), median_tokens=statistics.median(xs), max_tokens=max(xs),
                            coverage=cv)
    print('\nCoverage for native, sf-catalog and sf-expert is by construction (they are given or assumed to pick '
          'the labeled rules); for sf-hook and skillforge it is what retrieval actually delivered.')
    if a.json:
        Path(a.json).write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
