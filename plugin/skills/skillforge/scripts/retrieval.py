"""Rule-level retrieval over the library. Local, deterministic, no dependencies.

Every unit of guidance is a *rule*, from one of three layouts:
  - a curated reference file with title/tags frontmatter (rules/*.md, references/*.md);
  - one section of a procedural guide (systematic-debugging, TDD), split at its headings;
  - one entry of an authored rule pack (RULES.md), written as `## id: Title` plus
    `key: value` metadata lines and a body.
Imported source files are never edited or summarized; delivery only strips their
frontmatter and a heading that repeats the title (see compact()).

Ranking is BM25 over each rule's title, tags, keywords and body, with curated synonyms
at reduced weight. A technology prior then reorders and demotes: a technology the prompt
names outright (taxonomy `aliases`) strongly favours its rules and demotes other
technologies'; a weaker mention (`hints`) or the project's detected stack only nudges.
Priors never select a rule on their own: every delivered rule must clear MIN_SCORE on
word evidence alone.
"""
import json
import math
import os
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
# MIN_SCORE, RELATIVE, MIN_MATCHED and BRIEF_RELATIVE were chosen with
# forge/sweep_retrieval.py on the development sets only (dev, mixed, security, performance,
# tasks, negatives, ambiguous; 2,400-token budget): 12 / 0.75 / 2 / 0.55. MIN_SCORE 14 has a
# slightly higher F1 but leaves about twice as many prompts with no guidance, so it was not
# chosen. See docs/BENCHMARKS.md. The held-out set was scored once, after this choice.
MIN_SCORE = float(os.environ.get('SKILLFORGE_MIN_SCORE', '12.0'))
RELATIVE = float(os.environ.get('SKILLFORGE_RELATIVE', '0.75'))  # drop rules under this share of a part's best
PER_PART = 4        # at most this many rules per prompt part, unless coverage needs more
MAX_PER_PART = 7    # hard cap when a part names many technologies or concerns
NAMED_BOOST, OTHER_TECH, OFF_STACK, ON_STACK, HINT_BOOST = 2.0, 0.05, 0.5, 1.2, 1.3
# With no technology named, if the best rules from two different technologies score
# within this ratio, the part is ambiguous ("the orders page is slow": query or render?)
# and nothing is delivered for it rather than guessing.
AMBIGUOUS = 0.8
# With no technology named and no stack, a technology-specific rule must also match this
# many distinct prompt words in its title, tags and keywords (0 turns the guard off).
MIN_FIELD_HITS = int(os.environ.get('SKILLFORGE_MIN_FIELD_HITS', '2'))
EXPANDED_WEIGHT = 0.5  # weight of a query word recovered by expand() relative to one the prompt wrote
# Curated synonyms (synonyms.json) are OFF by default: on the development sets, weight 0.3
# added ~1.3 points of recall but cut abstention on unrelated prompts from 92.5% to 86.2%
# (forge/sweep_retrieval.py --synonym-weight 0,0.3,0.5). Opt in with SKILLFORGE_SYNONYM_WEIGHT.
SYNONYM_WEIGHT = float(os.environ.get('SKILLFORGE_SYNONYM_WEIGHT', '0'))
# Coordination: a rule must match at least this many distinct words the prompt wrote
# (synonyms and word forms do not count). One shared generic word ("write", "count",
# "green") was the main source of rules delivered for unrelated prompts.
MIN_MATCHED = int(os.environ.get('SKILLFORGE_MIN_MATCHED', '2'))
BRIEF_RELATIVE = float(os.environ.get('SKILLFORGE_BRIEF_RELATIVE', '0.55'))  # see interleave(); +4.6 pts precision, -1 pt recall
MAX_RULES = int(os.environ.get('SKILLFORGE_MAX_RULES', '0'))
COVERAGE_FLOOR = 0.6   # a named technology's coverage pick may score this share of MIN_SCORE
CLAUSE_FLOOR = 0.75    # a clause's coverage pick may score this share of MIN_SCORE
MIN_SECTION, MAX_SECTION = 500, 3500  # characters, for splitting procedural guides
TOKENIZER_VERSION = 2  # bump when terms()/stem() change, so cached indexes are rebuilt


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


_SPECIAL = [(re.compile(r'c\+\+'), ' cpp '), (re.compile(r'c#'), ' csharp '), (re.compile(r'(?<![a-z0-9])\.net\b'), ' dotnet '),
            (re.compile(r'\b([a-z0-9]+)\.js\b'), r'\1js'), (re.compile(r'\bn\s*\+\s*1\b'), ' nplusone ')]


def _special(text):
    text = text.lower()
    for pattern, repl in _SPECIAL:
        text = pattern.sub(repl, text)
    return text


def terms(text):
    """The one text normalizer: lowercase words, stemmed, stopwords removed, order kept.
    Framework names written as X.js become one word (Next.js reads as nextjs); C++, C#,
    .NET and N+1 become cpp, csharp, dotnet and nplusone."""
    return [stem(w) for w in re.findall(r'[a-z0-9]{2,}', _special(text)) if w not in STOP and stem(w) not in STOP]


def phrase_text(text):
    """Normalized text for whole-phrase matching of technology names: ' word word '."""
    return ' ' + ' '.join(re.findall(r'[a-z0-9@$]+', _special(text))) + ' '


def tokens(text):
    """Estimated tokens (characters / 4). An estimate, not a tokenizer count."""
    return math.ceil(len(text) / 4)


def _is_relative_to(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def read_safe(root, relative):
    path = (Path(root) / relative).resolve()
    if not _is_relative_to(path, Path(root).resolve()):
        raise ValueError(f'library path escapes root: {relative}')
    return path.read_text(encoding='utf-8')


def strip_frontmatter(text):
    front = re.match(r'\A---\s*\n(.*?)\n---[ \t]*(?:\n|$)', text, re.S)
    return (dict(re.findall(r'^(\w+):[ \t]*(.+)$', front[1], re.M)), text[front.end():]) if front else ({}, text)


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:60] or 'section'


def listing(value):
    """'a, b, c' or a list -> ['a', 'b', 'c']."""
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value or '').split(',') if v.strip()]


def compact(text, title=None):
    """Delivery form of a rule: frontmatter removed, a leading heading that repeats the
    title removed, runs of blank lines collapsed. Wording is otherwise untouched."""
    _, body = strip_frontmatter(text)
    body = body.strip()
    first = re.match(r'#{1,3} +(.+)\n', body)
    if first and title and slug(first[1]) == slug(title):
        body = body[first.end():].strip()
    return re.sub(r'\n{3,}', '\n\n', body)


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


PACK_HEADING = re.compile(r'^## ([a-z0-9][a-z0-9-]{0,63}): (.+)$')
PACK_FIELDS = ('tags', 'keywords', 'refs', 'technologies', 'requires', 'conflicts', 'versions', 'evidence')


def parse_pack(text):
    """(module header fields, [rule dict]) of an authored RULES.md.

    Headings inside fenced code blocks are ignored. Raises ValueError on a malformed
    entry, so a broken pack fails the build instead of silently losing rules."""
    header, body = strip_frontmatter(text)
    rules, current, fence = [], None, False
    for line in body.splitlines():
        if line.lstrip().startswith('```'):
            fence = not fence
        match = None if fence else PACK_HEADING.match(line)
        if match:
            current = {'name': match[1], 'title': match[2].strip(), 'meta': {}, 'lines': [], 'in_meta': True}
            rules.append(current)
            continue
        if current is None:
            continue
        if current['in_meta']:
            field = re.match(r'^(\w+):\s*(.*)$', line)
            if field and field[1] in PACK_FIELDS:
                current['meta'][field[1]] = field[2].strip()
                continue
            if not line.strip():
                current['in_meta'] = False
                continue
            current['in_meta'] = False
        current['lines'].append(line)
    out, seen = [], set()
    for r in rules:
        if r['name'] in seen:
            raise ValueError(f"duplicate rule id {r['name']!r} in pack")
        seen.add(r['name'])
        body = '\n'.join(r['lines']).strip()
        if not body:
            raise ValueError(f"rule {r['name']!r} has no body")
        if not r['meta'].get('tags'):
            raise ValueError(f"rule {r['name']!r} has no tags")
        out.append(dict(name=r['name'], title=r['title'], body=body, **r['meta']))
    return header, out


def eligible(index, mode=None):
    return [m for m in index['modules'] if m['kind'] == 'module' and m['status'] in ('provisional', 'preferred')
            and (mode is None or m['mode'] == mode)]


def _rule(module, rule_id, path, title, tags, text, body, **extra):
    r = dict(id=rule_id, module=module['name'], path=path, title=title, tags=tags, text=text, body=body,
             keywords=extra.pop('keywords', ''), refs=listing(extra.pop('refs', '')),
             technologies=listing(extra.pop('technologies', '')) or list(module.get('technologies', [])),
             versions=extra.pop('versions', ''))
    r.update(extra)
    return r


def load_rules(index, root, mode=None):
    """Every deliverable rule in the library, in a stable order."""
    rules = []
    for module in eligible(index, mode):
        found, inline = [], {}
        pack = module['path'] if module['path'].endswith('RULES.md') else None
        if pack:
            _, entries = parse_pack(read_safe(root, pack))
            for e in entries:
                refs = listing(e.get('refs', ''))
                delivered = e['body'] + ''.join(f'\nReference: {u}' for u in refs)
                found.append(_rule(module, f"{module['name']}/{e['name']}", f"{pack}#{e['name']}", e['title'],
                                   e['tags'], delivered, e['body'], keywords=e.get('keywords', ''),
                                   refs=refs, technologies=e.get('technologies', ''),
                                   versions=e.get('versions', ''), delivery=delivered))
                inline[e['name']] = {k: listing(e[k]) for k in ('requires', 'conflicts') if e.get(k)}
                if e.get('evidence'):
                    inline[e['name']]['evidence'] = e['evidence']
        for path in ([] if pack else sorted(set(module['references']))):
            p = Path(path)
            if p.suffix != '.md' or p.name.startswith('_') or p.parent.name not in ('rules', 'references'):
                continue
            text = read_safe(root, path)
            fields, body = strip_frontmatter(text)
            if fields.get('title') and fields.get('tags'):
                title = fields['title'].strip()
                found.append(_rule(module, f"{module['name']}/{p.stem}", path, title, fields['tags'], text, body,
                                   keywords=fields.get('keywords', ''), technologies=fields.get('technologies', ''),
                                   delivery=compact(text, title)))
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
                    found.append(_rule(module, f"{module['name']}/{prefix}{anchor}", f'{path}#{anchor}',
                                       f"{doc_title}: {'; '.join(headings) or 'Overview'}",
                                       ' '.join(module.get('applies', [])), section, section, delivery=section))
        attach_relations(module, found, inline)
        rules.extend(found)
    return rules


def attach_relations(module, found, inline=None):
    """Hand-declared requires/conflicts/evidence from the index (and, for packs, inline).
    Unknown names are errors, so a renamed section cannot silently drop a dependency."""
    declared = {k: dict(v) for k, v in (module.get('rules') or {}).items()}
    for name, meta in (inline or {}).items():
        declared.setdefault(name, {}).update(meta)
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
        if meta.get('keywords'):
            r['keywords'] = (r.get('keywords', '') + ' ' + str(meta['keywords'])).strip()


# ------------------------------------------------------------------ vocabulary files
_JSON_CACHE = {}


def _library_json(root, name, default):
    """A small JSON file next to index.json, read once per process. Missing -> default."""
    path = Path(root) / name if root else None
    key = str(path)
    if key not in _JSON_CACHE:
        try:
            _JSON_CACHE[key] = json.loads(path.read_text(encoding='utf-8')) if path else default
        except (OSError, ValueError):
            _JSON_CACHE[key] = default
    return _JSON_CACHE[key]


DEFAULT_LIBRARY = Path(__file__).resolve().parents[3] / 'library'


class Taxonomy:
    """Canonical technologies, how prompts name them, and what they imply."""

    def __init__(self, data):
        techs = (data or {}).get('technologies', {})
        self.names = set(techs)
        self.implies = {t: set(v.get('implies', [])) for t, v in techs.items()}
        self.strong, self.weak = [], []
        for t, v in techs.items():
            # Only listed aliases count: a canonical name such as "go", "c" or "cloud" is
            # an ordinary word in most prompts ("let us go to the next step").
            for alias in v.get('aliases', []):
                self.strong.append((phrase_text(alias), t))
            for alias in v.get('hints', []):
                self.weak.append((phrase_text(alias), t))
        self.canonical = {}
        for phrase, t in self.strong + self.weak:
            self.canonical.setdefault(phrase.strip(), t)
        self.packages = {p.lower(): t for t, v in techs.items() for p in v.get('packages', [])}
        self.files = {t: v.get('files', []) for t, v in techs.items()}

    @classmethod
    def load(cls, root=None):
        return cls(_library_json(root or DEFAULT_LIBRARY, 'technologies.json', {}))

    def canon(self, name):
        """A technology name or alias -> canonical name (unknown names pass through)."""
        key = phrase_text(name).strip()
        return name if name in self.names else self.canonical.get(key, key.replace(' ', '-'))

    def closure(self, techs):
        out, todo = set(), list(techs)
        while todo:
            t = todo.pop()
            if t not in out:
                out.add(t)
                todo.extend(self.implies.get(t, ()))
        return out

    def named(self, text):
        """(strong, weak): technologies a text names outright, and ones it only hints at."""
        p = phrase_text(text)
        strong = {t for phrase, t in self.strong if phrase in p}
        weak = {t for phrase, t in self.weak if phrase in p} - strong
        return strong, weak


def load_synonyms(root=None):
    """{stemmed term: {stemmed synonym, ...}} from synonyms.json groups."""
    data = _library_json(root or DEFAULT_LIBRARY, 'synonyms.json', {})
    out = {}
    for group in data.get('groups', []):
        stems = {t for word in group for t in terms(word)}
        for s in stems:
            out.setdefault(s, set()).update(stems - {s})
    return out


class Index:
    """BM25 over rules. Title, tags and keywords are counted twice: they are written to
    describe the rule. Code blocks stay in: identifiers such as customer_id link a rule to
    the reported symptom."""

    def __init__(self, rules, synonyms=None, docs=None):
        self.rules = rules
        self.synonyms = synonyms or {}
        self.docs = docs or [Counter(terms(f"{r['title']} {r['tags']} {r.get('keywords', '')} " * 2 + r['body']))
                             for r in rules]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / len(self.lengths) if rules else 1
        df = Counter(t for d in self.docs for t in d)
        n = len(rules)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.fields = {r['id']: set(terms(f"{r['title']} {r['tags']} {r.get('keywords', '')}")) for r in rules}
        self.position = {id(r): i for i, r in enumerate(rules)}
        self.postings = {}
        for i, d in enumerate(self.docs):
            for t in d:
                self.postings.setdefault(t, []).append(i)

    def expand(self, wanted):
        """{term: weight}. A comparative form on either side of the match gets one more
        chance: the prompt says "deep" and the rule says "deeper", or the other way round.
        Curated synonyms (synonyms.json) are added at SYNONYM_WEIGHT. Every added word must
        exist in the library vocabulary, so no unrelated word is invented, and an added
        word never outweighs one the prompt wrote."""
        out = {t: 1.0 for t in wanted}
        for t in wanted:
            candidates = [t + 'er', t + 'est']
            if t.endswith('er') and len(t) >= 6:
                candidates.append(stem(t[:-2]))
            elif t.endswith('est') and len(t) >= 7:
                candidates.append(stem(t[:-3]))
            for base in candidates:
                if base in self.idf and base not in out:
                    out[base] = EXPANDED_WEIGHT
            for syn in sorted(self.synonyms.get(t, ()) if SYNONYM_WEIGHT > 0 else ()):
                if syn in self.idf and syn not in out:
                    out[syn] = SYNONYM_WEIGHT
        return out

    def field_hits(self, rule_id, wanted):
        """How many distinct prompt words appear in the rule's title, tags and keywords."""
        return len(wanted.keys() & self.fields.get(rule_id, set()))

    def scores(self, query):
        """[(score, rule)] for every rule with any matching term (others score 0 and are omitted)."""
        wanted = self.expand(set(terms(query)))
        totals = {}
        for t, weight in wanted.items():
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i in self.postings[t]:
                tf = self.docs[i][t]
                totals[i] = totals.get(i, 0.0) + weight * idf * tf * (K1 + 1) / (
                    tf + K1 * (1 - B + B * self.lengths[i] / self.avg))
        return [(s, self.rules[i]) for i, s in sorted(totals.items())]

    def matched(self, rule_index, wanted):
        """Distinct prompt-written words (weight 1.0) that occur in the rule."""
        doc = self.docs[rule_index]
        return sum(1 for t, w in wanted.items() if w == 1.0 and t in doc)


def technologies(index, taxonomy=None):
    """{module: canonical technologies} from the index."""
    taxonomy = taxonomy or Taxonomy.load()
    return {m['name']: {taxonomy.canon(t) for t in m.get('technologies', [])} for m in index['modules']}


def rule_techs(rule, taxonomy):
    return {taxonomy.canon(t) for t in rule.get('technologies', [])}


def prior(own, named, stack, hinted=frozenset()):
    """Multiplier from technologies the prompt names, hints at, and the project stack.
    Rules with no technology (debugging, testing, security) are never demoted."""
    if not own:
        return 1.0
    if named:
        return NAMED_BOOST if own & named else OTHER_TECH
    factor = HINT_BOOST if own & hinted else 1.0
    if stack:
        return factor * (ON_STACK if own & stack else OFF_STACK)
    return factor


def split_prompt(text):
    """Sentences and lines of a free-text prompt; each is ranked on its own, so one long
    prompt describing several problems can reach a rule for each."""
    parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+|\n+', text) if p.strip()]
    return [p for p in parts if len(set(terms(p))) >= 2] or ([text.strip()] if text.strip() else [])


def clauses(part):
    """Comma, semicolon, 'and', 'with', 'plus' separated pieces of one sentence that carry
    at least two content words: "Next.js with PostgreSQL, Redis caching, JWT auth" ->
    concerns that each deserve a look."""
    pieces = re.split(r'[,;:]|\band\b|\bwith\b|\bplus\b|\balso\b|\bthen\b', part, flags=re.I)
    return [p.strip() for p in pieces if len(set(terms(p))) >= 2]


class Context:
    """Everything rank() needs that does not depend on the prompt: built once per library."""

    def __init__(self, index_data, rules, root=None, taxonomy=None, synonyms=None, docs=None, idx=None):
        self.taxonomy = taxonomy or Taxonomy.load(root)
        self.idx = idx or Index(rules, load_synonyms(root) if synonyms is None else synonyms, docs)
        self.techs = {r['id']: self.taxonomy.closure(rule_techs(r, self.taxonomy)) - {''} for r in rules}
        self.own = {r['id']: rule_techs(r, self.taxonomy) for r in rules}
        self.module_techs = technologies(index_data, self.taxonomy)


def rank(index_data, idx, parts, stack=(), context=None):
    """Per part, the rules worth delivering, best first: [(part, [(score, rule), ...])].

    `idx` may be an Index (built by the caller) or None when `context` is given."""
    if context is None:
        context = Context(index_data, idx.rules, idx=idx)
    tax, idx = context.taxonomy, context.idx
    whole = ' '.join(parts)
    named_direct, hinted = tax.named(whole)
    named = tax.closure(named_direct)
    stack_terms = tax.closure({tax.canon(s) for s in stack}) if stack else set()
    ranked = []
    for part in parts:
        def score(text, floor=MIN_SCORE, tech_credit=False):
            # The threshold applies to the evidence itself; priors only reorder and demote.
            out = []
            wanted_here = idx.expand(set(terms(text)))
            for s, r in idx.scores(text):
                if s < floor:
                    continue
                if MIN_MATCHED > 1:
                    # For a named technology's coverage pick, the rule's own technology named in
                    # the prompt counts as a matched word: Postgres rules rarely say "postgres".
                    hits_here = idx.matched(idx.position[id(r)], wanted_here) + bool(
                        tech_credit and context.own[r['id']] & named_direct)
                    if hits_here < MIN_MATCHED:
                        continue
                a = s * prior(context.own[r['id']], named, stack_terms, hinted)
                if a >= floor:
                    out.append((a, s, r))
            if not named and not stack_terms and MIN_FIELD_HITS:
                wanted = idx.expand(set(terms(text)))
                out = [x for x in out
                       if not context.own[x[2]['id']]
                       or idx.field_hits(x[2]['id'], wanted) >= MIN_FIELD_HITS]
            out.sort(key=lambda x: (-x[0], x[2]['id']))
            return out

        scored = score(part)
        if not named and ambiguous(scored, context):
            # Split between technologies: do not guess one. Rules that do not depend on the
            # technology (API design, security, testing) still apply if they clear the bar.
            generic = [x for x in scored if not context.own[x[2]['id']]]
            top = generic[0][0] if generic else 0
            ranked.append((part, Hits((round(a, 2), r) for a, _, r in generic
                                      if a >= RELATIVE * top)[:PER_PART] if generic else []))
            continue
        best = scored[0][0] if scored else 0
        kept = [x for x in scored if x[0] >= RELATIVE * best]
        # Coverage: each technology this part names outright, and each clause of a
        # multi-concern sentence, gets its best qualifying rule first, so a stronger
        # technology or concern cannot take every slot from a weaker one.
        own_named, _ = tax.named(part)
        firsts = []
        if len(own_named) >= 2:
            for tech in sorted(own_named):
                top = next((x for x in scored if tech in context.own[x[2]['id']]), None)
                if top is None:
                    top = next((x for x in score(part, MIN_SCORE * COVERAGE_FLOOR, tech_credit=True)
                                if tech in context.own[x[2]['id']]), None)
                if top and all(top[2] is not f[2] for f in firsts):
                    firsts.append(top)
        protected = {id(f[2]) for f in firsts}
        pieces = clauses(part)
        if len(pieces) >= 2:
            for piece in pieces:
                top = next(iter(score(piece, MIN_SCORE * CLAUSE_FLOOR)), None)
                if top and all(top[2] is not f[2] for f in firsts):
                    firsts.append(top)
        firsts.sort(key=lambda x: (-x[0], x[2]['id']))
        chosen = firsts + [x for x in kept if all(x[2] is not f[2] for f in firsts)]
        cap = min(MAX_PER_PART, max(PER_PART, len(firsts)))
        hits = Hits((round(a, 2), r) for a, _, r in chosen[:cap])
        hits.coverage = protected
        ranked.append((part, hits))
    return ranked


class Hits(list):
    """One part's ranked hits. `coverage` holds the rules picked to cover a technology the
    part names; the brief-level relative cut in interleave() never removes those."""
    coverage = frozenset()


def ambiguous(scored, context, allow_related=True):
    """True when the leading evidence is split between technologies."""
    best_by_tech = {}
    for adjusted, _, rule in scored:
        tech = frozenset(context.own.get(rule['id'], ()))
        if tech:
            best_by_tech.setdefault(tech, adjusted)
    ordered = sorted(best_by_tech.items(), key=lambda item: -item[1])
    if len(ordered) < 2 or not scored or ordered[0][1] != scored[0][0]:
        return False
    lead, lead_score = ordered[0]
    for other, score in ordered[1:]:
        if score < AMBIGUOUS * lead_score:
            break
        if not (allow_related and _techs_related(lead, other, context)):
            return True
    return False


def _techs_related(first, second, context):
    """Two leading technologies where one implies the other (Next.js and React, Postgres
    and SQL) are not a real split: the evidence agrees."""
    a, b = (context.taxonomy.closure(x) for x in (first, second))
    return bool(first <= b or second <= a)


# ------------------------------------------------------------------ project detection
PG_SQL = re.compile(r'generated\s+always\s+as\s+identity|timestamptz|jsonb|plpgsql|for\s+update\s+skip', re.I)
MANIFESTS = ('requirements.txt', 'requirements-dev.txt', 'pyproject.toml', 'Pipfile', 'go.mod', 'Cargo.toml',
             'pom.xml', 'build.gradle', 'build.gradle.kts', 'Gemfile', 'composer.json', 'pubspec.yaml')
MAX_MANIFEST_BYTES = 512_000


def _read(path, limit=MAX_MANIFEST_BYTES):
    try:
        with open(path, 'rb') as f:
            return f.read(limit).decode('utf-8', errors='replace')
    except OSError:
        return None


def detect_stack(folder, max_files=200, taxonomy=None):
    """Technologies and declared versions from a project's manifests, shallowly.

    Reads package.json dependencies, the other ecosystems' manifests (requirements, pyproject,
    go.mod, Cargo.toml, pom.xml, Gradle, Gemfile, composer.json, pubspec.yaml) at the top level,
    marker files from the taxonomy (Dockerfile, *.tf, .github/workflows, ...) at the top level or
    one below, and up to max_files .sql files two levels deep that use Postgres-only syntax.
    Files are read with a size cap and never executed. The result only reorders and demotes
    rules; it never selects one on its own.
    """
    tax = taxonomy or Taxonomy.load()
    folder = Path(folder)
    found, versions = set(), {}
    text = _read(folder / 'package.json')
    if text is not None:
        found.add('javascript')
        try:
            pkg = json.loads(text)
            for key in ('dependencies', 'devDependencies', 'peerDependencies'):
                deps = pkg.get(key) or {}
                if not isinstance(deps, dict):
                    continue
                for name, version in deps.items():
                    tech = tax.packages.get(str(name).lower())
                    if tech:
                        found.add(tech)
                        versions[name] = str(version)
        except (ValueError, AttributeError):
            pass
    for name in MANIFESTS:
        text = _read(folder / name)
        if text is None:
            continue
        low = text.lower()
        for package, tech in tax.packages.items():
            # Go module paths may carry a major-version suffix (github.com/jackc/pgx/v5).
            if re.search(r'(?:^|[\s"\'/:])' + re.escape(package) + r'(?=[\s<>=~!\[;"\':,/]|$)', low, re.M):
                found.add(tech)
    for tech, patterns in tax.files.items():
        for pattern in patterns:
            try:
                if any(folder.glob(pattern)) or any(folder.glob('*/' + pattern)):
                    found.add(tech)
                    break
            except (OSError, ValueError):
                continue
    if 'postgres' not in found:
        sql = [*folder.glob('*.sql'), *folder.glob('*/*.sql'), *folder.glob('*/*/*.sql')][:max_files]
        for path in sql:
            content = _read(path, 20000)
            if content and PG_SQL.search(content):
                found.add('postgres')
                break
    return sorted(found), versions


def interleave(ranked):
    """Round-robin across parts so every problem in the prompt gets its best rule first.

    BRIEF_RELATIVE drops a hit scoring under that share of the best hit in the whole prompt,
    so a weak match from a filler sentence ("Fix it.") cannot ride along with a strong
    one. MAX_RULES (0 = no cap) bounds the number of ranked rules per brief."""
    out, seen = [], set()
    best = max((h[0] for _, hits in ranked for h in hits if h[0] is not None), default=0)
    floor = BRIEF_RELATIVE * best
    depth = max((len(hits) for _, hits in ranked), default=0)
    for i in range(depth):
        for _, hits in ranked:
            if i < len(hits) and hits[i][1]['id'] not in seen:
                protected = id(hits[i][1]) in getattr(hits, 'coverage', ())
                if hits[i][0] is not None and hits[i][0] < floor and not protected:
                    continue
                seen.add(hits[i][1]['id'])
                out.append(hits[i])
    return out[:MAX_RULES] if MAX_RULES else out
