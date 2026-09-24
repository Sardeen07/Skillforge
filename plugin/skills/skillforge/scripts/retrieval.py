"""Rule-level retrieval over the library. Local, deterministic, no dependencies.

Every unit of guidance is a *rule*: a curated reference file with title/tags
frontmatter, or one section of a procedural guide (systematic-debugging, TDD) split
at its headings when loaded. Source files are never edited or summarized.

Ranking is BM25 over each rule's title, tags and body text, then a
technology prior: naming a technology in the prompt, or passing it as the project
stack, strongly favours that technology's rules and demotes other technologies'.
"""
import json
import math
import re
from collections import Counter
from pathlib import Path

STOP = frozenset('''
a about after again all also an and any are as at be because been before being but by can
could did do does doing done each even ever every for from get gets getting had has have having
he her here his how i if in into is it its just keep make makes me more most my need needs no
not now of off on once one only or other our out over please same should so some such than that
the their them then there these they this those through to too up us use using very want was
way we were what when where whether which while who why will with would you your
fix improve performance code faster slow slower
'''.split())
# fix/improve/performance/code/slow describe almost every task, so they cannot tell rules apart.

K1, B = 1.2, 0.75
# MIN_SCORE was the lowest threshold at which all 6 unrelated development prompts abstain.
# It was tuned on seen cases; confirm it on a held-out set before trusting it.
MIN_SCORE = 8.0     # below this score a rule is not relevant enough to deliver (abstain)
RELATIVE = 0.45     # within one prompt part, drop rules scoring under this share of the best
PER_PART = 4        # at most this many rules per prompt part (3 drops pagination from the benchmark paragraph)
NAMED_BOOST, OTHER_TECH, OFF_STACK, ON_STACK = 2.0, 0.2, 0.5, 1.2
# With no technology named, if the best rules from two different technologies score
# within this ratio, the part is ambiguous ("the orders page is slow": query or render?)
# and nothing is delivered for it rather than guessing.
AMBIGUOUS = 0.8
MIN_SECTION, MAX_SECTION = 500, 3500  # characters, for splitting procedural guides


def stem(word):
    """Light suffix stripping so 'paging'/'pages', 'locked'/'locks', 'queries'/'query' meet."""
    if word.endswith('ies') and len(word) > 4:
        return word[:-3] + 'y'
    for suffix in ('ing', 'ed'):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[:-len(suffix)]
            if len(word) > 3 and word[-1] == word[-2] and word[-1] not in 'lsz':
                word = word[:-1]  # running -> run, but not fill -> fil
            return word
    if word.endswith('s') and not word.endswith('ss') and len(word) > 3:
        word = word[:-1]
    if word.endswith('e') and len(word) > 3:
        word = word[:-1]  # page/paging, cache/cached, queue/queued
    return word


def terms(text):
    """The one text normalizer: lowercase words, stemmed, stopwords removed, order kept.
    Framework names written as X.js become one word, so Next.js reads as nextjs."""
    text = re.sub(r'\b([a-z0-9]+)\.js\b', r'\1js', text.lower())
    return [stem(w) for w in re.findall(r'[a-z0-9]{2,}', text) if w not in STOP and stem(w) not in STOP]


def tokens(text):
    """Estimated tokens (characters / 4). An estimate, not a tokenizer count."""
    return math.ceil(len(text) / 4)


def read_safe(root, relative):
    path = (Path(root) / relative).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError(f'library path escapes root: {relative}')
    return path.read_text(encoding='utf-8')


def strip_frontmatter(text):
    front = re.match(r'\A---\s*\n(.*?)\n---[ \t]*(?:\n|$)', text, re.S)
    return (dict(re.findall(r'^(\w+):\s*(.+)$', front[1], re.M)), text[front.end():]) if front else ({}, text)


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:60] or 'section'


def split_sections(text):
    """(headings, text) chunks of a procedural guide, at '## ' and, inside long sections, '### '.

    Short neighbouring chunks are merged so no unit is a two-line fragment.
    """
    _, body = strip_frontmatter(text)
    pieces = []
    for chunk in re.split(r'(?m)^(?=## )', body):
        pieces.extend(re.split(r'(?m)^(?=### )', chunk) if len(chunk) > MAX_SECTION else [chunk])
    merged = []
    for piece in pieces:
        if not piece.strip():
            continue
        heading = re.match(r'#{2,3} (.+)', piece)
        headings = [heading[1].strip()] if heading else []
        if merged and (len(merged[-1][1]) < MIN_SECTION or len(piece) < MIN_SECTION):
            merged[-1][0].extend(headings)
            merged[-1][1] += piece
        else:
            merged.append([headings, piece])
    return [(h, t.strip()) for h, t in merged]


def eligible(index, mode=None):
    return [m for m in index['modules'] if m['kind'] == 'module' and m['status'] in ('provisional', 'preferred')
            and (mode is None or m['mode'] == mode)]


def load_rules(index, root, mode=None):
    """Every deliverable rule in the library, in a stable order."""
    rules = []
    for module in eligible(index, mode):
        found = []
        for path in sorted(set(module['references'])):
            p = Path(path)
            if p.suffix != '.md' or p.name.startswith('_') or p.parent.name not in ('rules', 'references'):
                continue
            text = read_safe(root, path)
            fields, body = strip_frontmatter(text)
            if fields.get('title') and fields.get('tags'):
                found.append(dict(id=f"{module['name']}/{p.stem}", module=module['name'], path=path,
                                  title=fields['title'].strip(), tags=fields['tags'], text=text, body=body))
        if not found:
            # A procedural guide with no rule files: its sections become the rules.
            docs = [module['path']] + sorted(r for r in module['references'] if r.endswith('.md')
                                             and not Path(r).name.startswith(('_', 'README', 'CHANGELOG', 'LICENSE')))
            for path in docs:
                text = read_safe(root, path)
                title = re.search(r'(?m)^# (.+)$', text)
                doc_title = title[1].strip() if title else Path(path).stem
                # IDs: module/section for the main guide, module/doc#section for supporting docs.
                prefix = '' if path == module['path'] else f'{Path(path).stem}#'
                seen = Counter()
                for headings, section in split_sections(text):
                    name = slug(headings[0]) if headings else 'overview'
                    seen[name] += 1
                    anchor = name if seen[name] == 1 else f'{name}-{seen[name]}'
                    found.append(dict(id=f"{module['name']}/{prefix}{anchor}", module=module['name'],
                                      path=f'{path}#{anchor}',
                                      title=f"{doc_title}: {'; '.join(headings) or 'Overview'}",
                                      tags=' '.join(module.get('applies', [])), text=section, body=section))
        attach_relations(module, found)
        rules.extend(found)
    return rules


def attach_relations(module, found):
    """Hand-declared requires/conflicts/evidence from the index. Unknown names are errors,
    so a renamed section cannot silently drop a dependency."""
    declared = module.get('rules') or {}
    ids = {r['id'] for r in found}
    full = lambda name: name if '/' in name else f"{module['name']}/{name}"
    for name, meta in declared.items():
        for target in [name, *meta.get('requires', []), *meta.get('conflicts', [])]:
            if full(target) not in ids and '/' not in target:
                raise ValueError(f"{module['name']}: rule relation names unknown rule {target!r}")
    for r in found:
        meta = declared.get(r['id'][len(module['name']) + 1:], {})
        r['requires'] = [full(t) for t in meta.get('requires', [])]
        r['conflicts'] = [full(t) for t in meta.get('conflicts', [])]
        r['evidence'] = meta.get('evidence', 'untested')


class Index:
    """BM25 over rules. Title and tags are counted twice: they are written to describe the rule.
    Code blocks stay in: identifiers such as customer_id link a rule to the reported symptom."""

    def __init__(self, rules):
        self.rules = rules
        self.docs = [Counter(terms(f"{r['title']} {r['tags']} " * 2 + r['body'])) for r in rules]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / len(self.lengths) if rules else 1
        df = Counter(t for d in self.docs for t in d)
        n = len(rules)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def scores(self, query):
        wanted = set(terms(query))
        out = []
        for rule, doc, length in zip(self.rules, self.docs, self.lengths):
            s = 0.0
            for t in wanted & doc.keys():
                tf = doc[t]
                s += self.idf[t] * tf * (K1 + 1) / (tf + K1 * (1 - B + B * length / self.avg))
            out.append((s, rule))
        return out


def technologies(index):
    return {m['name']: {stem(t) for t in m.get('technologies', [])} for m in index['modules']}


def prior(module, named, stack, techs):
    """Multiplier from technologies the prompt names and the project stack. Modules with
    no technology (debugging, testing) are never demoted."""
    own = techs.get(module, set())
    if not own:
        return 1.0
    if named:
        return NAMED_BOOST if own & named else OTHER_TECH
    if stack:
        return ON_STACK if own & stack else OFF_STACK
    return 1.0


def split_prompt(text):
    """Sentences and lines of a free-text prompt; each is ranked on its own, so one long
    prompt describing several problems can reach a rule for each."""
    parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+|\n+', text) if p.strip()]
    return [p for p in parts if len(set(terms(p))) >= 2] or ([text.strip()] if text.strip() else [])


def rank(index_data, idx, parts, stack=()):
    """Per part, the rules worth delivering, best first: [(part, [(score, rule), ...])]."""
    techs = technologies(index_data)
    all_tech = set().union(*techs.values()) if techs else set()
    named = set(terms(' '.join(parts))) & all_tech
    stack_terms = set(terms(' '.join(stack))) & all_tech
    ranked = []
    for part in parts:
        # The threshold applies to the evidence itself; priors only reorder and demote.
        # (Letting a named technology count toward it was measured: "fix a slow postgres
        # query" then drew four generic Postgres rules, and dev recall fell.)
        scored = [(s * prior(r['module'], named, stack_terms, techs), s, r)
                  for s, r in idx.scores(part) if s >= MIN_SCORE]
        scored = [x for x in scored if x[0] >= MIN_SCORE]
        scored.sort(key=lambda x: (-x[0], x[2]['id']))
        if not named and ambiguous(scored, techs):
            ranked.append((part, []))
            continue
        best = scored[0][0] if scored else 0
        kept = [x for x in scored if x[0] >= RELATIVE * best]
        # Explicitly mixed: each technology this part names gets its best qualifying rule
        # first, so a stronger technology cannot take every slot from a weaker one.
        own = set(terms(part)) & all_tech
        firsts = []
        if len({m for m, t in techs.items() if t & own}) >= 2:
            for module in sorted({m for m, t in techs.items() if t & own}):
                top = next((x for x in scored if x[2]['module'] == module), None)
                if top:
                    firsts.append(top)
            firsts.sort(key=lambda x: (-x[0], x[2]['id']))
        chosen = firsts + [x for x in kept if x not in firsts]
        ranked.append((part, [(round(a, 2), r) for a, _, r in chosen][:PER_PART]))
    return ranked


def ambiguous(scored, techs):
    """True when the leading evidence is split between technologies."""
    best_by_tech = {}
    for adjusted, _, rule in scored:
        tech = frozenset(techs.get(rule['module'], ()))
        if tech:
            best_by_tech.setdefault(tech, adjusted)
    tops = sorted(best_by_tech.values(), reverse=True)
    return (len(tops) >= 2 and scored and tops[0] == scored[0][0]
            and tops[1] >= AMBIGUOUS * tops[0])


PACKAGES = {'react': 'react', 'react-dom': 'react', 'next': 'nextjs', 'pg': 'postgres', 'postgres': 'postgres',
            'pg-promise': 'postgres', '@supabase/supabase-js': 'supabase', '@neondatabase/serverless': 'postgres',
            'psycopg': 'postgres', 'psycopg2': 'postgres', 'psycopg2-binary': 'postgres', 'asyncpg': 'postgres',
            'supabase': 'supabase'}
PG_SQL = re.compile(r'generated\s+always\s+as\s+identity|timestamptz|jsonb|plpgsql|for\s+update\s+skip', re.I)


def detect_stack(folder, max_files=200):
    """Technologies and declared versions from a project's manifests, shallowly.

    Reads package.json, requirements*.txt and pyproject.toml at the top level, and up to
    max_files .sql files two levels deep that use Postgres-only syntax. The result only
    reorders and demotes rules; it never selects one on its own.
    """
    folder = Path(folder)
    found, versions = set(), {}
    try:
        pkg = json.loads((folder / 'package.json').read_text(encoding='utf-8'))
        for deps in (pkg.get('dependencies') or {}, pkg.get('devDependencies') or {}):
            for name, version in deps.items():
                if name in PACKAGES:
                    found.add(PACKAGES[name])
                    versions[name] = str(version)
    except (OSError, ValueError, AttributeError):
        pass
    for path in [*folder.glob('requirements*.txt'), folder / 'pyproject.toml']:
        try:
            text = path.read_text(encoding='utf-8').lower()
        except OSError:
            continue
        for name, tech in PACKAGES.items():
            if re.search(r'(?:^|[\s"\'])' + re.escape(name) + r'(?=[\s<>=~!\[;"\']|$)', text, re.M):
                found.add(tech)
    sql = [*folder.glob('*.sql'), *folder.glob('*/*.sql'), *folder.glob('*/*/*.sql')][:max_files]
    for path in sql:
        try:
            if PG_SQL.search(path.read_text(encoding='utf-8', errors='replace')[:20000]):
                found.add('postgres')
                break
        except OSError:
            continue
    return sorted(found), versions


def interleave(ranked):
    """Round-robin across parts so every problem in the prompt gets its best rule first."""
    out, seen = [], set()
    depth = max((len(hits) for _, hits in ranked), default=0)
    for i in range(depth):
        for _, hits in ranked:
            if i < len(hits) and hits[i][1]['id'] not in seen:
                seen.add(hits[i][1]['id'])
                out.append(hits[i])
    return out
