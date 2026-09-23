"""Local, deterministic rule retrieval and bounded delivery. No API or dependencies.

Only curated rule directories with title/tag frontmatter are indexed. Full rule bodies
are delivered verbatim, never summarized or cut mid-example. This is extractive
selection, not a claim of semantic equivalence or measured model improvement.
"""
import copy
import hashlib
import math
import re
from collections import Counter
from pathlib import Path

from compose import compose, words

STOP = words('a an the this that to of for in on with and or is are be it from by as use using '
             'when only all should can have has not how why fix improve performance code')


def terms(text):
    # Keep one form per word: plural + singular must not count as two signals.
    result = set()
    for word in re.findall(r'[a-z0-9]+', text.lower()):
        if word.endswith('ies') and len(word) > 4:
            word = word[:-3] + 'y'
        elif word.endswith('s') and len(word) > 3:
            word = word[:-1]
        result.add(word)
    return result - STOP


def tokens(text):
    return math.ceil(len(text) / 4)


def read_safe(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'library path escapes root: {relative}')
    return path.read_text(encoding='utf-8')


def catalog(index, root):
    rules = []
    for module in index['modules']:
        if module['status'] not in ('provisional', 'preferred'):
            continue
        for path in sorted(set(module['references'])):
            p = Path(path)
            if p.suffix != '.md' or p.name.startswith('_') or p.parent.name not in ('rules', 'references'):
                continue
            text = read_safe(root, path)
            front = re.match(r'\A---\s*\n(.*?)\n---(?:\n|$)', text, re.S)
            if not front:
                continue
            fields = dict(re.findall(r'^(title|tags):\s*(.+)$', front[1], re.M))
            if not fields.get('title') or not fields.get('tags'):
                continue
            # First prose paragraph adds symptoms, but not identifiers from examples.
            paragraphs = text[front.end():].strip().split('\n\n')
            intro = next((p for p in paragraphs if not p.startswith(('#', '```'))), '')
            rules.append({'module': module['name'], 'path': path, 'text': text,
                          'terms': terms(fields['title'] + ' ' + fields['tags'] + ' ' + intro),
                          'tags': terms(fields['tags'])})
    return rules


def rank_rules(rules, task):
    query = terms(task)
    freq = Counter(t for rule in rules for t in rule['terms'])
    ranked = []
    for rule in rules:
        hits = query & rule['terms']
        # A single generic body word must not activate a module.
        if len(hits) < 2 and not any(t in rule['tags'] and freq[t] <= 2 for t in hits):
            continue
        score = sum(math.log(1 + len(rules) / freq[t]) for t in hits)
        ranked.append((score, rule))
    return sorted(ranked, key=lambda pair: (-pair[0], pair[1]['path']))


def build_brief(index, root, mode, subtasks, stack=(), budget=None, emitted=(), delivery='rules', routing='references'):
    """Return text, content-addressed session keys, and a machine-readable audit.

    Module conflict/dependency selection is shared between delivery arms. The final
    budget includes headings, provenance, and omission notices. Cached units are
    omitted only if their path AND content match; new references remain eligible.
    """
    if delivery not in ('rules', 'modules'):
        raise ValueError('unknown delivery mode')
    root = Path(root)
    idx = copy.deepcopy(index)
    cfg = idx['modes'].get(mode)
    if cfg is None:
        raise ValueError(f'unknown mode: {mode}')
    budget = cfg['budget_tokens'] if budget is None else budget
    if budget <= 0:
        raise ValueError('budget must be positive')
    if routing not in ('keywords', 'references'):
        raise ValueError('unknown routing mode')
    rules = catalog(idx, root)
    per_task = [rank_rules(rules, task) for task in subtasks]
    # Use reference evidence to reach a module even without its technology name.
    for module in idx['modules']:
        if routing == 'references':
            module['_rule_matches'] = [
                (sorted(words(task)), max((score for score, r in ranking
                                          if r['module'] == module['name']), default=0))
                for task, ranking in zip(subtasks, per_task)]
        # Enforce the budget on the actual serialized payload below, not stale
        # MODULE.md estimates (which exclude reference files and wrappers).
        module['est_tokens'] = 0
    selected, _, _, selection = compose(idx, mode, subtasks, stack, budget)
    required = {req['target'] for m in selected for req in m['requires']}
    units = []
    audit = []
    for module in selected:
        matches = []
        for ranking in per_task:
            matches.extend((score, r) for score, r in ranking if r['module'] == module['name'])
        unique = {}
        for score, rule in matches:
            old = unique.get(rule['path'])
            if old is None or score > old[0]:
                unique[rule['path']] = (score, rule)
        ordered = sorted(unique.values(), key=lambda x: (-x[0], x[1]['path']))
        # Only modules with matching standalone rules use extractive delivery.
        # Required modules and procedural guides retain their complete text.
        if delivery == 'rules' and ordered and module['name'] not in required and module['kind'] != 'core':
            units.extend((module, r['path'], r['text'], score) for score, r in ordered[:4])
        else:
            body = read_safe(root, module['path'])
            if ordered:
                body += '\nRelevant reference files (read before applying this index):\n'
                body += ''.join(f"- {(root / r['path']).resolve()}\n" for _, r in ordered[:4])
            units.append((module, module['path'], body, None))
    header = f'# SkillForge brief: {mode}\nDelivery: {delivery}. Budget: {budget} estimated tokens (characters / 4).\n'
    notice = ('\nApply guidance only where it fits the task; preserve required behavior. '
              'Examples are not complete application designs. '
              'Only the units below were delivered in this call.\n')
    if tokens(header + notice) > budget:
        raise ValueError('budget too small for brief envelope')
    out = header
    keys = set()
    seen_body = set()
    delivered_modules = set()
    # Dependencies appear first in compose's topological ordering. If one cannot
    # fit, skip its dependent too instead of emitting incomplete requirements.
    for module, path, body, score in units:
        digest = hashlib.sha256(body.encode('utf-8')).hexdigest()
        key = f'unit:{path}:{digest}'
        entry = {'module': module['name'], 'path': path, 'sha256': digest, 'relevance': score}
        deps = {req['target'] for req in module['requires']}
        if not deps <= delivered_modules:
            entry['result'] = 'missing dependency payload'
        elif key in emitted or digest in seen_body:
            entry['result'] = 'session hit' if key in emitted else 'duplicate content'
            delivered_modules.add(module['name'])
            keys.add(key)
        else:
            source = module.get('source') or {}
            origin = f"\nSource: {source['repo']}@{source['commit']}" if source else ''
            block = f"\n## {module['name']} / {path}{origin}\n\n{body.strip()}\n"
            if tokens(out + block + notice) > budget:
                if module['kind'] == 'core':
                    raise ValueError('budget too small for complete core and envelope')
                entry['result'] = 'over budget'
            else:
                out += block
                keys.add(key)
                seen_body.add(digest)
                delivered_modules.add(module['name'])
                entry['result'] = 'delivered'
        audit.append(entry)
    brief = out + notice
    selection.update({'delivery': delivery, 'routing': routing, 'estimated_output_tokens': tokens(brief),
                      'units': audit, 'delivered_modules': sorted(delivered_modules)})
    return brief, keys, selection
