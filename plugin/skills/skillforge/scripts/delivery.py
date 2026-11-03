"""Bounded delivery: a brief of complete rules, a catalog of every rule, or rules by ID.

Rules are ranked globally (see retrieval.py) and grouped by module only for display.
Full rule text is delivered verbatim, never summarized or cut mid-example. This is
extractive selection, not a claim of measured model improvement.
"""
import copy
import fnmatch
import hashlib
import json
from pathlib import Path

from retrieval import Context, Taxonomy, interleave, load_rules, rank, read_safe, split_prompt, tokens

NOTICE = ('\nApply guidance only where it fits the task; preserve required behavior. '
          'Examples are not complete application designs. '
          'Only the units below were delivered in this call.\n')


_CONTEXTS = {}


def _fingerprint(index, root, mode):
    """Identity of a loaded library: the index content plus each rule file's size and mtime.
    A changed file therefore rebuilds the in-process cache instead of serving stale text."""
    h = hashlib.sha256(json.dumps(index, sort_keys=True, default=str).encode('utf-8'))
    h.update(f'{Path(root).resolve()}|{mode}'.encode('utf-8'))
    for m in index.get('modules', []):
        for rel in [m.get('path', ''), *m.get('references', [])]:
            try:
                st = (Path(root) / rel).stat()
                h.update(f'{rel}:{st.st_size}:{st.st_mtime_ns}'.encode('utf-8'))
            except OSError:
                h.update(f'{rel}:missing'.encode('utf-8'))
    return h.hexdigest()


def library(index, root, mode, with_context=False):
    """(mode config, rules[, retrieval context]). Loaded rules and the BM25 index are
    cached per process, keyed by the library fingerprint."""
    cfg = index['modes'].get(mode)
    if cfg is None:
        raise ValueError(f"unknown mode: {mode!r}; available: {', '.join(index['modes'])}")
    key = _fingerprint(index, root, mode)
    if key not in _CONTEXTS:
        rules = load_rules(index, root, mode)
        _CONTEXTS.clear()
        _CONTEXTS[key] = (rules, Context(index, rules, root) if rules else None)
    rules, context = _CONTEXTS[key]
    return (cfg, rules, context) if with_context else (cfg, rules)


def closure(rule, by_id, active=()):
    """The rule plus its declared dependencies, dependencies first. Raises on a cycle."""
    if rule['id'] in active:
        raise ValueError(f"rule dependency cycle through {rule['id']}")
    out = []
    for dep in rule.get('requires', []):
        if dep not in by_id:
            raise ValueError(f"{rule['id']} requires unknown rule {dep}")
        out += [r for r in closure(by_id[dep], by_id, (*active, rule['id'])) if r not in out]
    return out + [rule]


def build_brief(index, root, mode, subtasks, stack=(), budget=None, emitted=(), delivery='rules',
                split=False, abstain_empty=False, rule_ids=None):
    """Return text, content-addressed session keys, and a machine-readable audit.

    subtasks are ranked separately and interleaved, so each gets its best rule first.
    split=True also splits each into sentences (for a raw prompt). abstain_empty=True
    returns an empty brief when no rule matches, instead of the core alone.
    rule_ids delivers exactly those rules instead of ranking (the expert-selection arm).

    A rule is delivered together with every rule it declares it requires, or not at all;
    a rule that conflicts with one already delivered is refused. The budget covers the
    whole serialized brief. Cached units are omitted only when their path AND content
    match what this session already received.
    """
    if delivery not in ('rules', 'modules'):
        raise ValueError('unknown delivery mode')
    root = Path(root)
    index = copy.deepcopy(index)
    cfg, rules, context = library(index, root, mode, with_context=True)
    by_id = {r['id']: r for r in rules}
    budget = cfg['budget_tokens'] if budget is None else budget
    if budget <= 0:
        raise ValueError('budget must be positive')
    if rule_ids is not None:
        unknown = [i for i in rule_ids if i not in by_id]
        if unknown:
            raise ValueError(f"unknown rule IDs: {', '.join(unknown)}")
        ranked = [('(fixed selection)', [(None, by_id[i]) for i in rule_ids])]
    else:
        parts = [p for task in subtasks for p in (split_prompt(task) if split else [task])]
        ranked = rank(index, None, parts, stack, context=context) if rules and parts else []
    picked = interleave(ranked)
    by_name = {m['name']: m for m in index['modules']}
    core = by_name.get(cfg['core'])
    if core is None:
        raise ValueError(f"core module {cfg['core']!r} is missing")

    header = f'# SkillForge brief: {mode}\nDelivery: {delivery}. Budget: {budget} estimated tokens (characters / 4).\n'
    if tokens(header + NOTICE) > budget:
        raise ValueError('budget too small for brief envelope')

    def block(module, path, body, rule=None, required_by=None):
        notes = [attribution(module)] if module.get('source') else []
        if rule:
            notes.append(f"evidence: {rule.get('evidence', 'untested')}")
            if required_by:
                notes.append(f'needed by {required_by}')
        title = f"{rule['id']}: {rule['title']}" if rule else f"{module['name']} / {path}"
        origin = '\n_' + ' · '.join(n for n in notes if n) + '_' if notes else ''
        return f'\n## {title}{origin}\n\n{body.strip()}\n'

    def entry(module, path, body, score, rule_id, required_by=None):
        digest = hashlib.sha256(body.encode('utf-8')).hexdigest()
        return {'id': rule_id, 'module': module['name'], 'path': path, 'sha256': digest,
                'relevance': score, 'required_by': required_by, 'key': f'unit:{path}:{digest}'}

    size = len(header + NOTICE)
    placed, keys, seen_body, delivered, audit, done = [], set(), set(), set(), [], set()

    def commit(group):
        """Place a group of (entry, block) all together if it fits the budget."""
        nonlocal size
        new = [(e, b) for e, b in group if e['key'] not in emitted and e['sha256'] not in seen_body]
        cost = sum(len(b) for _, b in new)
        if -(-(size + cost) // 4) > budget:
            return False
        size += cost
        for e, b in group:
            keys.add(e['key'])
            delivered.add(e['module'])
            if any(e is n for n, _ in new):
                placed.append((e, b))
                seen_body.add(e['sha256'])
                e['result'] = 'delivered'
            else:
                e['result'] = 'session hit' if e['key'] in emitted else 'duplicate content'
        return True

    core_body = read_safe(root, core['path'])
    core_entry = entry(core, core['path'], core_body, None, core['name'])
    audit.append(core_entry)
    if not commit([(core_entry, block(core, core['path'], core_body))]):
        raise ValueError('budget too small for complete core and envelope')

    if delivery == 'rules':
        for score, rule in picked:
            if rule['id'] in done:
                continue
            members = [r for r in closure(rule, by_id) if r['id'] not in done]
            group = []
            for r in members:
                dep_of = rule['id'] if r is not rule else None
                module = by_name[r['module']]
                text = r.get('delivery', r['text'])
                e = entry(module, r['path'], text, score if r is rule else None, r['id'], dep_of)
                audit.append(e)
                group.append((e, block(module, r['path'], text, r, dep_of)))
            clash = [c for r in members for c in r.get('conflicts', []) if c in done]
            clash += [d for d in done for r in members if r['id'] in by_id[d].get('conflicts', [])]
            if clash:
                for e, _ in group:
                    e['result'] = f'refused: conflicts with {clash[0]}'
            elif commit(group):
                done.update(r['id'] for r in members)
            else:
                for e, _ in group:
                    e['result'] = 'over budget' if len(group) == 1 else 'over budget (with its dependencies)'
    else:
        # Delivery ablation: each matched module's full MODULE.md plus the matched rule paths.
        for name in dict.fromkeys(r['module'] for _, r in picked):
            m = by_name[name]
            body = read_safe(root, m['path'])
            paths = [r['path'].split('#')[0] for _, r in picked if r['module'] == name]
            if any(p != m['path'] for p in paths):
                body += '\nRelevant reference files (read before applying this index):\n'
                body += ''.join(f'- {(root / p).resolve()}\n' for p in dict.fromkeys(paths) if p != m['path'])
            e = entry(m, m['path'], body, max((s or 0) for s, r in picked if r['module'] == name), name)
            audit.append(e)
            if not commit([(e, block(m, m['path'], body))]):
                e['result'] = 'over budget'

    # Read in module order; within a module, dependencies stay ahead of what needs them.
    order = list(dict.fromkeys(e['module'] for e, _ in placed))
    out = header + ''.join(b for name in order for e, b in placed if e['module'] == name)
    for e in audit:
        e.pop('key')
    if abstain_empty and not any(e['result'] == 'delivered' for e in audit[1:]):
        brief = ''
    else:
        brief = out + NOTICE
    matched = [e for e in audit[1:] if e['result'] in ('delivered', 'session hit')]
    log = {'mode': mode, 'budget': budget, 'subtasks': list(subtasks), 'stack': list(stack), 'delivery': delivery,
           'parts': [{'text': part, 'rules': [{'id': r['id'], 'score': s} for s, r in hits]} for part, hits in ranked],
           'misses': [part for part, hits in ranked if not hits],
           'units': audit, 'delivered_modules': sorted(delivered) if brief else [],
           'matched_rules': [e['id'] for e in matched],
           'estimated_output_tokens': tokens(brief), 'output_chars': len(brief)}
    return brief, keys, log


def attribution(module):
    """'repo@commit12 (license)' for imported modules, 'authored (license)' for packs."""
    src = module.get('source') or {}
    if not src:
        return ''
    lic = src.get('license') or 'license unknown'
    if src.get('kind') == 'authored':
        return f"SkillForge-authored ({lic})"
    return f"{src.get('repo')}@{str(src.get('commit', ''))[:12]} ({lic})"


CATALOG_INTRO = ('When one fits the task, fetch its full text before changing code (ID = <module>/<name>):\n'
                 '  {fetch} --rule <id> [--rule <id> ...]\n'
                 'Fetch only rules that fit; each costs roughly 150-800 tokens. Most tasks need none or a few.')


def catalog_text(index, root, mode, fetch_command, module=None, budget=2400, stack=()):
    """The menu of rules at a small, bounded cost.

    Full form (no budget, or the whole catalog fits): one line per rule under its module.
    Two-level form (the full catalog would exceed `budget` estimated tokens): one line per
    module with its rule count, then full rule lists for the modules on the detected
    stack while they fit; `--catalog <module>` lists the rest. module=NAME lists just
    that module's rules.
    """
    _, rules = library(index, Path(root), mode)
    by_module = {}
    for r in rules:
        by_module.setdefault(r['module'], []).append(r)
    info = {m['name']: m for m in index['modules']}
    if module is not None:
        if module not in by_module:
            raise ValueError(f"unknown module {module!r}; run --catalog for the list")
        by_module = {module: by_module[module]}

    def rule_lines(name, group):
        cap = info[name].get('capability')
        out = [f"\n## {name}" + (f" ({cap})" if cap else '')]
        out += [f"{r['id'][len(name) + 1:]}: {r['title'].split(': ', 1)[-1][:90]}" for r in group]
        return out

    head = [f'# SkillForge catalog: {mode}',
            f'{sum(len(g) for g in by_module.values())} curated rules in {len(by_module)} modules.',
            CATALOG_INTRO.format(fetch=fetch_command)]
    full = head + [line for name, group in by_module.items() for line in rule_lines(name, group)]
    text = '\n'.join(full) + '\n'
    if module is not None or tokens(text) <= budget:
        return text
    lines = head + [f'List one module\'s rules with: {fetch_command} --catalog <module>', '', '## modules']
    for name, group in by_module.items():
        cap = info[name].get('capability') or ''
        lines.append(f"{name} ({len(group)}): {cap}"[:110])
    tax = Taxonomy.load(root)
    stack = tax.closure({tax.canon(s) for s in stack})
    for name, group in by_module.items():
        own = {tax.canon(t) for t in info[name].get('technologies', [])}
        if stack and own & stack:
            extra = rule_lines(name, group)
            if tokens('\n'.join(lines + extra) + '\n') <= budget:
                lines += extra
    return '\n'.join(lines) + '\n'


def get_rules(index, root, mode, ids):
    """Full text of the named rules. Accepts module/id or an unambiguous id suffix."""
    _, rules = library(index, Path(root), mode)
    by_id = {r['id']: r for r in rules}
    out, missing = [], []
    for want in ids:
        rule = by_id.get(want)
        if rule is None:
            hits = [r for r in rules if r['id'].endswith(want) or r['id'].endswith('/' + want)
                    or fnmatch.fnmatch(r['id'], want)]
            rule = hits[0] if len(hits) == 1 else None
        if rule is None:
            missing.append(want)
            continue
        out.append(f"## {rule['id']}: {rule['title']}\n\n{rule.get('delivery', rule['text']).strip()}\n")
    return '\n'.join(out), missing
