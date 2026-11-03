#!/usr/bin/env python3
"""Find Claude skills on GitHub and vet them into *candidates*. Nothing here edits the library.

    scan.py scan owner/repo[@ref] ...  [--seeds FILE] [--out data/candidates.jsonl] [--emit PATH]
    scan.py seeds-from-json FILE        owner/repo names found in any JSON (e.g. a Skills Directory dump)

For every SKILL.md in a repo, pinned to one commit, the scanner records its license, size,
risk flags and overlap with the existing library, then gives a verdict:

    known    already in the library (same upstream folder or name); nothing to do
    accept   passed every check; safe to import as a *candidate* (never auto-promoted)
    review   a person has to look: scripts, an unclear license, near-duplicate text, odd metadata
    reject   blocked: proprietary or missing license, prompt-injection text, hidden characters

The verdict is triage, not a security audit. The regexes below catch careless and blatant
problems only. Read every accepted skill before importing it, and treat everything fetched
here as untrusted data: the scanner reads text and never runs anything it downloads.

Two backends give the same facts. `git` (default) shallow-clones each repo: no key, no rate
limit, but no star count or archived flag. `api` uses the GitHub API: those two extras, but
anonymous use allows ~60 requests/hour (3 per repo), so set GITHUB_TOKEN for real runs.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin/skills/skillforge/scripts'))
from retrieval import Index, load_rules, strip_frontmatter, terms, tokens, MIN_SCORE  # noqa: E402

ALLOWED = {'mit', 'apache-2.0', 'bsd', 'isc', 'cc0-1.0', 'unlicense'}
MIN_TOKENS, MAX_TOKENS = 150, 6000        # estimated, characters / 4
NEAR_DUPLICATE = 0.5                      # share of the smaller text's 5-word runs found in the other
SCRIPT_EXT = {'.sh', '.bash', '.zsh', '.py', '.js', '.mjs', '.ts', '.rb', '.pl', '.ps1', '.bat', '.cmd'}
SPDX = {'mit': 'MIT', 'apache-2.0': 'Apache-2.0', 'bsd': 'BSD', 'isc': 'ISC', 'cc0-1.0': 'CC0-1.0', 'unlicense': 'Unlicense'}
NAME_OK = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')

# (id, pattern, severity). 'reject' blocks the skill, 'review' sends it to a person.
RISKS = [
    ('ignore-instructions', r'(ignore|disregard|forget)\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier|system)\s+(instructions|rules|prompts?)', 'reject'),
    ('pipe-to-shell', r'(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh\b', 'reject'),
    ('decode-and-run', r'base64\s+(-d|--decode)[^\n]*\|\s*(ba|z)?sh\b|\b(eval|exec)\(\s*(atob|base64|b64|compile)', 'reject'),
    ('hardcoded-secret', r'(api[_-]?key|secret|token|password)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{20,}', 'reject'),
    ('credential-paths', r'~/\.ssh|\.aws/credentials|id_rsa|/etc/passwd', 'reject'),
    ('dynamic-eval', r'\beval\(', 'review'),
    ('destructive', r'\brm\s+-rf\b|\bchmod\s+777\b|\bmkfs\b|:\(\)\s*\{', 'review'),
    ('privilege', r'\bsudo\b', 'review'),
    ('remote-fetch', r'\b(curl|wget)\s+(-\w+\s+)*https?://', 'review'),
]
# Zero-width and bidi-control characters can hide instructions from a human reviewer.
HIDDEN = re.compile('[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]')


# ------------------------------------------------------------------ GitHub access
class GitHub:
    """The only part that touches the network; tests replace it."""

    def __init__(self, token=None):
        self.token = token or os.environ.get('GITHUB_TOKEN')

    def get(self, url):
        req = urllib.request.Request(url, headers={'User-Agent': 'skillforge-scan'})
        if self.token and 'api.github.com' in url:
            req.add_header('Authorization', f'Bearer {self.token}')
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as e:
            hint = ' (rate limited: set GITHUB_TOKEN)' if e.code in (403, 429) else ''
            raise RuntimeError(f'{e.code} for {url}{hint}')

    def api(self, path):
        return json.loads(self.get('https://api.github.com' + path))

    def repo(self, repo):
        d = self.api(f'/repos/{repo}')
        return dict(stars=d.get('stargazers_count'), license=(d.get('license') or {}).get('spdx_id'),
                    archived=d.get('archived', False), fork=d.get('fork', False))

    def resolve(self, repo, ref):
        return self.api(f'/repos/{repo}/commits/{urllib.parse.quote(ref or "HEAD")}')['sha']

    def tree(self, repo, sha):
        d = self.api(f'/repos/{repo}/git/trees/{sha}?recursive=1')
        return d['tree'], d.get('truncated', False)

    def raw(self, repo, sha, path):
        return self.get(f'https://raw.githubusercontent.com/{repo}/{sha}/{urllib.parse.quote(path)}')


class GitCheckout:
    """Same interface as GitHub, from a shallow clone. Downloaded files are only read, never
    run; symlinks are skipped so a repo cannot point the scanner at files outside itself."""

    def __init__(self, base='https://github.com/', workdir=None):
        self.base = base
        self.work = Path(workdir or tempfile.mkdtemp(prefix='skillforge-scan-'))
        self.dirs = {}

    def _git(self, *args, cwd=None):
        env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1')
        r = subprocess.run(['git', '-c', 'core.symlinks=false', '-c', 'core.hooksPath=/dev/null', *args],
                           cwd=cwd, env=env, capture_output=True, text=True, timeout=180)
        if r.returncode:
            raise RuntimeError(f"git {args[0]} failed: {r.stderr.strip()[:200]}")
        return r.stdout.strip()

    def _clone(self, repo):
        if repo not in self.dirs:
            dest = self.work / repo.replace('/', '__')
            self._git('clone', '--quiet', '--depth', '1', '--no-tags', self.base + repo, str(dest))
            self.dirs[repo] = dest
        return self.dirs[repo]

    def repo(self, repo):
        root = self._clone(repo)
        lic = next((p for p in sorted(root.glob('*')) if re.fullmatch(r'licen[sc]e(\.\w+)?', p.name.lower())
                    and p.is_file() and not p.is_symlink()), None)
        text = lic.read_text(encoding='utf-8', errors='replace')[:1500] if lic else None
        return dict(stars=None, license=text, archived=False, fork=False)

    def resolve(self, repo, ref):
        root = self._clone(repo)
        if ref:
            self._git('fetch', '--quiet', '--depth', '1', 'origin', ref, cwd=root)
            self._git('checkout', '--quiet', 'FETCH_HEAD', cwd=root)
        return self._git('rev-parse', 'HEAD', cwd=root)

    def tree(self, repo, sha):
        root, out = self.dirs[repo], []
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != '.git' and not (Path(dirpath) / d).is_symlink()]
            for f in files:
                p = Path(dirpath) / f
                if p.is_symlink():
                    continue
                out.append(dict(path=p.relative_to(root).as_posix(), type='blob',
                                mode='100755' if os.access(p, os.X_OK) else '100644'))
        return out, False

    def raw(self, repo, sha, path):
        return (self.dirs[repo] / path).read_text(encoding='utf-8', errors='replace')

    def cleanup(self):
        shutil.rmtree(self.work, ignore_errors=True)


# ------------------------------------------------------------------ checks
def normalize_license(text):
    """Map free text or an SPDX id to a key in ALLOWED, 'proprietary', 'gpl', or None (unrecognized)."""
    t = (text or '').lower()
    if not t.strip() or t.strip() == 'noassertion':
        return None
    if re.search(r'proprietary|all rights reserved|source[- ]available|not licensed|no license', t):
        return 'proprietary'
    if re.search(r'apache', t): return 'apache-2.0'
    if re.search(r'\bmit\b|permission is hereby granted', t): return 'mit'
    if re.search(r'\bbsd\b|redistribution and use in source', t): return 'bsd'
    if re.search(r'\bisc\b', t): return 'isc'
    if re.search(r'cc0|creative commons zero', t): return 'cc0-1.0'
    if re.search(r'unlicense', t): return 'unlicense'
    if re.search(r'gpl|general public license|agpl', t): return 'gpl'
    return None


def effective_license(sources):
    """Most restrictive recognized license wins; sources is {where: text}. -> (key, where)."""
    found = {where: normalize_license(text) for where, text in sources.items() if text}
    for key in ('proprietary', 'gpl'):
        for where, k in found.items():
            if k == key:
                return key, where
    for where in ('file', 'frontmatter', 'repo'):
        if found.get(where) in ALLOWED:
            return found[where], where
    return (None, 'unrecognized') if any(sources.values()) else (None, 'none')


def risk_flags(text):
    flags = [dict(id=i, severity=s) for i, p, s in RISKS if re.search(p, text, re.I)]
    if HIDDEN.search(text):
        flags.append(dict(id='hidden-characters', severity='reject'))
    return flags


def shingles(text, n=5):
    words = re.findall(r'[a-z0-9]+', text.lower())
    return {' '.join(words[i:i + n]) for i in range(max(len(words) - n + 1, 0))}


def containment(a, b):
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def suggest_applies(name, description, limit=12):
    """Starting keywords for a curator to edit, from the skill's own name and description."""
    seen = []
    for t in terms(name.replace('-', ' ') + ' ' + description):
        if len(t) >= 3 and t not in seen:
            seen.append(t)
    return seen[:limit]


class Library:
    """What is already in the library: for near-duplicate and overlap checks."""

    def __init__(self, root=ROOT / 'plugin/library'):
        index = json.loads((root / 'index.json').read_text(encoding='utf-8'))
        self.rules = [r for r in load_rules(index, root) if len(r['text']) > 400]
        self.sets = [(r['id'], shingles(r['text'])) for r in self.rules]
        self.bm25 = Index(self.rules)
        # Anything already imported, whatever its status, by upstream folder and by name.
        self.known = {}
        for m in index['modules']:
            src = m.get('source') or {}
            if src.get('repo'):
                self.known[(src['repo'].lower(), src.get('path', '').strip('/'))] = m['name']
            self.known[m['name']] = m['name']
        for folder in (root / 'modules').glob('*'):
            self.known.setdefault(folder.name, folder.name)

    def already_have(self, repo, path, name):
        folder = path.rsplit('/', 1)[0] if '/' in path else ''
        return self.known.get((repo.lower(), folder)) or self.known.get(name)

    def duplicate_of(self, text):
        mine = shingles(text)
        best = max(((containment(mine, s), i) for i, s in self.sets), default=(0.0, None))
        return best if best[0] >= NEAR_DUPLICATE else (best[0], None)

    def nearest(self, description):
        best = max(self.bm25.scores(description), key=lambda x: x[0], default=(0.0, None))
        return (round(best[0], 1), best[1]['id']) if best[1] and best[0] >= MIN_SCORE else (round(best[0], 1), None)


def vet(skill, library, seen):
    """One skill dict in, one candidate record out. `seen` maps content hash -> first repo/path."""
    text = skill['text']
    fields, body = strip_frontmatter(text)
    name, desc = fields.get('name', '').strip().strip('"\''), fields.get('description', '').strip().strip('"\'')
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    reject, review = [], []
    have = library.already_have(skill['repo'], skill['path'], name)

    if not name or not desc:
        review.append('frontmatter needs a single-line name and description')
    elif not NAME_OK.match(name):
        review.append(f'name {name!r} is not lowercase letters, digits and hyphens (max 64)')
    if len(desc) > 1024:
        review.append('description is over 1024 characters')

    lic, lic_from = effective_license(dict(skill['license_sources'], frontmatter=fields.get('license')))
    if lic == 'proprietary':
        reject.append(f'license is proprietary ({lic_from})')
    elif lic is None and lic_from == 'none':
        reject.append('no license anywhere, so no right to redistribute')
    elif lic == 'gpl':
        review.append('GPL-family license; check it can be redistributed inside this repo')
    elif lic is None:
        review.append('license text not recognized; read it')

    flags = risk_flags(text)
    reject += [f"risk: {f['id']}" for f in flags if f['severity'] == 'reject']
    review += [f"risk: {f['id']}" for f in flags if f['severity'] == 'review']

    if skill['scripts']:
        review.append(f"ships {len(skill['scripts'])} script file(s); the importer would copy them into the library")
    n = tokens(text)
    if n < MIN_TOKENS:
        review.append(f'only ~{n} tokens; too thin to carry guidance')
    elif n > MAX_TOKENS:
        review.append(f'~{n} tokens; needs splitting into rules before it can be delivered')
    if skill['archived']:
        review.append('repository is archived')

    dup_score, dup_rule = library.duplicate_of(body)
    if dup_rule:
        review.append(f'text overlaps library rule {dup_rule} ({dup_score:.0%} of its wording)')
    first = seen.setdefault(digest, f"{skill['repo']}/{skill['path']}")
    duplicate_of = first if first != f"{skill['repo']}/{skill['path']}" else None
    if duplicate_of:
        review.append(f'identical to {duplicate_of}')
    near_score, near_rule = library.nearest(f'{name} {desc}')

    return dict(repo=skill['repo'], path=skill['path'], commit=skill['commit'], name=name, description=desc[:300],
                license=lic, license_from=lic_from, stars=skill['stars'], est_tokens=n, content_hash=digest,
                scripts=skill['scripts'], risk=flags,
                verdict='known' if have and not reject else 'reject' if reject else 'review' if review else 'accept',
                reasons=([f'already in the library as {have}'] if have else []) + reject + review, duplicate_of=duplicate_of, nearest_library_rule=near_rule,
                nearest_score=near_score, suggested_applies=suggest_applies(name, desc),
                scanned_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))


# ------------------------------------------------------------------ scanning
def parse_seed(line):
    line = line.split('#')[0].strip()
    if not line:
        return None
    repo, _, ref = line.partition('@')
    return (repo.strip(), ref.strip() or None) if re.fullmatch(r'[\w.-]+/[\w.-]+', repo.strip()) else None


def skills_in_repo(gh, repo, ref=None, limit=None):
    """Yield skill dicts for every SKILL.md in repo at one resolved commit."""
    info = gh.repo(repo)
    sha = gh.resolve(repo, ref)
    tree, truncated = gh.tree(repo, sha)
    if truncated:
        print(f'  warning: {repo} tree was truncated by GitHub; some skills may be missing', file=sys.stderr)
    blobs = [t for t in tree if t.get('type') == 'blob']
    paths = [t['path'] for t in blobs]
    modes = {t['path']: t.get('mode') for t in blobs}
    found = [p for p in paths if p.rsplit('/', 1)[-1].lower() == 'skill.md']
    for path in found[:limit]:
        folder = path.rsplit('/', 1)[0] + '/' if '/' in path else ''
        inside = [p for p in paths if p.startswith(folder) and p != path]
        scripts = [p for p in inside if Path(p).suffix.lower() in SCRIPT_EXT or modes.get(p) == '100755']
        sources = {'repo': info['license']}
        lic_file = next((p for p in inside if re.fullmatch(r'license(\.\w+)?', p[len(folder):].lower())), None)
        if lic_file:
            sources['file'] = gh.raw(repo, sha, lic_file)[:1500]
        yield dict(repo=repo, path=path, commit=sha, text=gh.raw(repo, sha, path), scripts=scripts,
                   license_sources=sources, stars=info['stars'], archived=info['archived'])


def scan(gh, repos, library, limit=None):
    seen, records = {}, []
    for repo, ref in repos:
        print(f'{repo}' + (f'@{ref}' if ref else ''))
        try:
            for skill in skills_in_repo(gh, repo, ref, limit):
                rec = vet(skill, library, seen)
                records.append(rec)
                print(f"  {rec['verdict']:6} {rec['path']}" + (f"  - {rec['reasons'][0]}" if rec['reasons'] else ''))
        except (RuntimeError, KeyError, ValueError) as e:
            print(f'  error: {e}', file=sys.stderr)
            records.append(dict(repo=repo, path=None, verdict='error', reasons=[str(e)]))
    return records


def emit_curation(records, path, base=ROOT / 'forge/curation/coding.json'):
    """A curation file the existing `sf.py import` understands, holding accepted skills only,
    all with status 'candidate' so they stay out of retrieval until a person promotes them.
    `applies` and `technologies` are suggestions to edit; overlap_group defaults to the name."""
    cur = json.loads(base.read_text(encoding='utf-8'))
    existing = {m['name'] for m in cur['modules']}
    modules = []
    for r in records:
        if r.get('verdict') != 'accept' or r['name'] in existing:
            continue
        modules.append(dict(name=r['name'], source=dict(repo=r['repo'], commit=r['commit'],
                       path=r['path'].rsplit('/', 1)[0] if '/' in r['path'] else '.', license=SPDX.get(r['license'], r['license'])),
                       capability=r['description'][:120], overlap_group=r['name'], applies=r['suggested_applies'],
                       technologies=[], status='candidate',
                       notes=f"scanned {r['scanned_at']}; stars={r['stars']}; ~{r['est_tokens']} tokens; "
                             f"nearest library rule: {r['nearest_library_rule'] or 'none'}. Not yet read by a person."))
    cur['modules'] = modules
    cur.pop('rules_note', None)
    Path(path).write_text(json.dumps(cur, indent=2) + '\n', encoding='utf-8')
    return len(modules)


def summary(records):
    counts = {}
    for r in records:
        counts[r['verdict']] = counts.get(r['verdict'], 0) + 1
    return ', '.join(f'{n} {v}' for v, n in sorted(counts.items())) or 'nothing found'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sc = sub.add_parser('scan')
    sc.add_argument('repos', nargs='*', help='owner/repo or owner/repo@ref')
    sc.add_argument('--seeds', help='file with one owner/repo[@ref] per line')
    sc.add_argument('--out', default=str(ROOT / 'data/candidates.jsonl'))
    sc.add_argument('--emit', help='also write a curation file of accepted skills (status candidate)')
    sc.add_argument('--limit', type=int, help='at most this many skills per repo')
    sc.add_argument('--backend', choices=('git', 'api'), default='git')
    sj = sub.add_parser('seeds-from-json')
    sj.add_argument('file')
    a = ap.parse_args()
    if a.cmd == 'seeds-from-json':
        names = sorted(set(re.findall(r'github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?(?=["/\s?#]|$)', Path(a.file).read_text(encoding='utf-8'))))
        print('\n'.join(names))
        return
    repos = [s for s in map(parse_seed, a.repos) if s]
    if a.seeds:
        repos += [s for s in map(parse_seed, Path(a.seeds).read_text(encoding='utf-8').splitlines()) if s]
    if not repos:
        ap.error('give at least one owner/repo, or --seeds FILE')
    source = GitCheckout() if a.backend == 'git' else GitHub()
    try:
        records = scan(source, repos, Library(), a.limit)
    finally:
        if hasattr(source, 'cleanup'):
            source.cleanup()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')
    print(f'\n{summary(records)} -> {out}')
    if a.emit:
        print(f'{emit_curation(records, a.emit)} accepted skills written to {a.emit} (status candidate)')


if __name__ == '__main__':
    main()
