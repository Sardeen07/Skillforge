"""Tests for the v1 library format, retrieval guards, delivery limits and benchmark integrity."""
import fnmatch, json, os, re, subprocess, sys, tempfile, time, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugin/skills/skillforge/scripts'
LIB = ROOT / 'plugin/library'
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / 'forge'))
import retrieval  # noqa: E402
from delivery import build_brief, catalog_text, library  # noqa: E402
from retrieval import Taxonomy, compact, detect_stack, parse_pack, terms  # noqa: E402

INDEX = json.loads((LIB / 'index.json').read_text(encoding='utf-8'))


def delivered(text, **kw):
    _, _, log = build_brief(INDEX, LIB, 'coding', [text], split=True, **kw)
    return [u['id'] for u in log['units'][1:] if u['result'] == 'delivered']


class TaxonomyDetection(unittest.TestCase):
    def setUp(self):
        self.t = Taxonomy.load(LIB)

    def test_aliases_and_special_spellings(self):
        for text, tech in [('Next.js app', 'nextjs'), ('PostgreSQL 16', 'postgres'), ('our k8s cluster', 'kubernetes'),
                           ('C++ service', 'cpp'), ('C# API', 'csharp'), ('.NET 8', 'csharp'), ('golang worker', 'go'),
                           ('React Native screen', 'react-native'), ('Spring Boot app', 'spring')]:
            strong, _ = self.t.named(text)
            self.assertIn(tech, strong, text)

    def test_ambiguous_words_are_not_technologies(self):
        for text in ('let us go to the next step', 'a swift response', 'express your concerns', 'see the next page',
                     'each node in the tree', 'add guard rails', 'track the cargo shipments', 'a vitamin c supplement'):
            strong, _ = self.t.named(text)
            self.assertFalse(strong & {'go', 'swift', 'express', 'nextjs', 'node', 'ruby', 'rust', 'c'}, (text, strong))
        for text, tech in (('our Express app', 'express'), ('the Rails app', 'ruby'), ('a Node.js service', 'node')):
            self.assertIn(tech, self.t.named(text)[0], text)

    def test_hints_never_count_as_named(self):
        strong, weak = self.t.named('the query is slow')
        self.assertNotIn('sql', strong)
        self.assertIn('sql', weak)

    def test_implications(self):
        self.assertLessEqual({'react', 'javascript'}, self.t.closure({'nextjs'}))
        self.assertIn('sql', self.t.closure({'postgres'}))

    def test_missing_taxonomy_degrades_gracefully(self):
        empty = Taxonomy({})
        self.assertEqual(empty.named('Postgres and React'), (set(), set()))


class StackDetection(unittest.TestCase):
    def test_manifests_and_marker_files(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / 'go.mod').write_text('module x\n\nrequire github.com/jackc/pgx/v5 v5.5.0\n')
            (d / 'Dockerfile').write_text('FROM golang:1.23\n')
            (d / '.github/workflows').mkdir(parents=True)
            (d / '.github/workflows/ci.yml').write_text('on: push\n')
            (d / 'main.tf').write_text('terraform {}\n')
            found, _ = detect_stack(d)
            for tech in ('go', 'postgres', 'docker', 'github-actions', 'terraform'):
                self.assertIn(tech, found)

    def test_package_json_versions_and_bad_json(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'package.json').write_text(json.dumps({'dependencies': {'next': '15.0.0', 'redis': '^4'}}))
            found, versions = detect_stack(d)
            self.assertLessEqual({'nextjs', 'redis', 'javascript'}, set(found))
            self.assertEqual(versions['next'], '15.0.0')
            Path(d, 'package.json').write_text('{not json')
            self.assertEqual(set(detect_stack(d)[0]), {'javascript', 'node'}, 'bad JSON still reads as a JS project')

    def test_large_manifest_is_capped(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'requirements.txt').write_text('x\n' * 2_000_000 + 'django\n')
            start = time.perf_counter()
            found, _ = detect_stack(d)
            self.assertLess(time.perf_counter() - start, 5)
            self.assertNotIn('django', found, 'reads past the size cap')


class PackFormat(unittest.TestCase):
    PACK = ('---\nmodule: demo\n---\n\n## first-rule: First rule\ntags: a, b, c\nrefs: https://example.org/x\n\n'
            'Body one.\n\n```md\n## not-a-rule: inside a fence\n```\n\n## second-rule: Second\ntags: d\n\nBody two.\n')

    def test_parses_rules_and_ignores_fenced_headings(self):
        _, rules = parse_pack(self.PACK)
        self.assertEqual([r['name'] for r in rules], ['first-rule', 'second-rule'])
        self.assertIn('## not-a-rule', rules[0]['body'])

    def test_malformed_packs_fail_loudly(self):
        with self.assertRaises(ValueError):
            parse_pack(self.PACK + '\n## first-rule: Duplicate\ntags: x\n\nAgain.\n')
        with self.assertRaises(ValueError):
            parse_pack('## no-tags: Missing tags\n\nBody.\n')
        with self.assertRaises(ValueError):
            parse_pack('## empty: Empty\ntags: x\n\n')

    def test_every_pack_rule_has_metadata_and_a_reference(self):
        _, rules = library(INDEX, LIB, 'coding')
        packs = [r for r in rules if r['path'].split('#')[0].endswith('RULES.md')]
        self.assertGreater(len(packs), 500)
        for r in packs:
            self.assertTrue(r['refs'] and all(u.startswith('https://') for u in r['refs']), r['id'])
            self.assertGreaterEqual(len([t for t in r['tags'].split(',') if t.strip()]), 3, r['id'])
            self.assertEqual(r['evidence'], 'untested', r['id'])

    def test_rule_ids_are_unique(self):
        _, rules = library(INDEX, LIB, 'coding')
        ids = [r['id'] for r in rules]
        self.assertEqual(len(ids), len(set(ids)))


class Compaction(unittest.TestCase):
    def test_removes_frontmatter_and_repeated_title(self):
        text = '---\ntitle: Use X\ntags: a\n---\n\n## Use X\n\nDo X.\n\n\n\nThen Y.\n'
        self.assertEqual(compact(text, 'Use X'), 'Do X.\n\nThen Y.')

    def test_keeps_a_different_heading(self):
        self.assertTrue(compact('## Background\n\nText', 'Use X').startswith('## Background'))

    def test_delivery_is_smaller_than_source_for_imported_rules(self):
        _, rules = library(INDEX, LIB, 'coding')
        imported = [r for r in rules if r['path'].endswith('.md') and '/rules/' in r['path'] or '/references/' in r['path']]
        self.assertTrue(imported)
        self.assertLess(sum(len(r['delivery']) for r in imported), sum(len(r['text']) for r in imported))


class RetrievalGuards(unittest.TestCase):
    def test_one_shared_generic_word_selects_nothing(self):
        for text in ('count how many words are in this paragraph', 'change the primary color from blue to green'):
            self.assertEqual(delivered(text), [], text)

    def test_abstention_floor_on_unrelated_and_ambiguous_prompts(self):
        # Measured 44/50 and 30/30 on 2026-11-05; known misses include "write a short poem"
        # (matches "write transactions short"). The floor guards against regressions.
        for name, floor in (('negatives', 0.85), ('ambiguous', 0.95)):
            cases = [json.loads(l) for l in (ROOT / 'benchmarks/retrieval' / f'{name}.jsonl').read_text().splitlines() if l.strip()]
            silent = sum(not delivered(c['task'], budget=2400) for c in cases)
            self.assertGreaterEqual(silent / len(cases), floor, f'{name}: {silent}/{len(cases)} abstained')

    def test_empty_whitespace_unicode_and_huge_prompts(self):
        for text in ('', '   ', '\n\n', '🙂🙂🙂', 'ß' * 50):
            self.assertEqual(delivered(text), [], repr(text))
        huge = 'our postgres workers block each other in the job queue. ' * 2000
        start = time.perf_counter()
        got = delivered(huge, budget=2400)
        self.assertLess(time.perf_counter() - start, 30)
        self.assertIn('postgres/lock-skip-locked', got)

    def test_directive_example_covers_several_concerns_within_budget(self):
        text = ('Build a scalable Next.js application with PostgreSQL, Redis caching, JWT authentication, '
                'and optimized database queries.')
        brief, _, log = build_brief(INDEX, LIB, 'coding', [text], budget=2400, split=True, abstain_empty=True)
        got = [u['id'] for u in log['units'][1:] if u['result'] == 'delivered']
        areas = {'nextjs': ('nextjs/', 'react-performance/'), 'postgres': ('postgres/', 'sql/', 'database-design/'),
                 'redis': ('redis/', 'distributed-systems/cache'), 'auth': ('auth/',)}
        covered = {k for k, prefixes in areas.items() if any(g.startswith(prefixes) for g in got)}
        self.assertGreaterEqual(len(covered), 3, got)
        self.assertLessEqual(retrieval.tokens(brief), 2400)

    def test_named_technology_coverage_survives_the_brief_cut(self):
        got = delivered('Fix the React request waterfall and the Postgres pagination query.', budget=2400)
        self.assertTrue([g for g in got if g.startswith(('postgres/', 'sql/'))], got)
        self.assertTrue([g for g in got if g.startswith(('react-performance/', 'nextjs/'))], got)

    def test_brief_relative_cut_drops_weak_riders(self):
        old = retrieval.BRIEF_RELATIVE
        try:
            retrieval.BRIEF_RELATIVE = 0.0
            loose = delivered('Our Postgres workers wait on each other. Fix it. Also the logs.', budget=5000)
            retrieval.BRIEF_RELATIVE = 0.55
            tight = delivered('Our Postgres workers wait on each other. Fix it. Also the logs.', budget=5000)
        finally:
            retrieval.BRIEF_RELATIVE = old
        self.assertLessEqual(len(tight), len(loose))
        self.assertTrue(set(tight) <= set(loose))

    def test_synonyms_are_off_by_default_and_never_invent_words(self):
        _, _, ctx = library(INDEX, LIB, 'coding', with_context=True)
        self.assertEqual(retrieval.SYNONYM_WEIGHT, 0)
        old = retrieval.SYNONYM_WEIGHT
        try:
            retrieval.SYNONYM_WEIGHT = 0.3
            expanded = ctx.idx.expand({retrieval.stem('synchronous')})
            self.assertTrue(all(t in ctx.idx.idf for t in expanded if expanded[t] < 1))
            self.assertTrue(any(w < 1 for w in expanded.values()))
        finally:
            retrieval.SYNONYM_WEIGHT = old

    def test_retrieval_is_fast_after_first_load(self):
        delivered('warm up the cache')
        start = time.perf_counter()
        for _ in range(20):
            delivered('our postgres workers block each other in the job queue', budget=2400)
        self.assertLess((time.perf_counter() - start) / 20, 0.25)


class CatalogLimits(unittest.TestCase):
    def test_two_level_catalog_fits_the_hook_budget(self):
        text = catalog_text(INDEX, LIB, 'coding', 'compose.py', budget=2400)
        self.assertLessEqual(retrieval.tokens(text), 2400)
        self.assertIn('--catalog <module>', text)

    def test_module_catalog_lists_its_rules(self):
        text = catalog_text(INDEX, LIB, 'coding', 'compose.py', module='redis')
        self.assertIn('avoid-keys-command', text)
        with self.assertRaises(ValueError):
            catalog_text(INDEX, LIB, 'coding', 'compose.py', module='no-such-module')

    def test_stack_modules_are_expanded_when_they_fit(self):
        text = catalog_text(INDEX, LIB, 'coding', 'compose.py', budget=2400, stack=['redis'])
        self.assertIn('avoid-keys-command', text)


class HookFallbacks(unittest.TestCase):
    def run_hook(self, env):
        payload = json.dumps({'hook_event_name': 'UserPromptSubmit', 'session_id': 'v1', 'cwd': tempfile.gettempdir(),
                              'prompt': 'our postgres workers block each other in the job queue'}).encode()
        with tempfile.TemporaryDirectory() as d:
            full = {**os.environ, 'SKILLFORGE_LOG': str(Path(d) / 'log'), 'SKILLFORGE_HOOK': 'brief', **env}
            r = subprocess.run([sys.executable, str(SCRIPTS / 'hook.py')], input=payload, capture_output=True,
                               env=full, timeout=60)
        self.assertEqual(r.returncode, 0)
        out = r.stdout.decode().strip()
        return json.loads(out)['hookSpecificOutput']['additionalContext'] if out else ''

    def test_invalid_budget_falls_back_to_default(self):
        for bad in ('abc', '-5', '10', '999999999'):
            text = self.run_hook({'SKILLFORGE_HOOK_BUDGET': bad})
            self.assertIn('Budget: 2400', text, bad)

    def test_catalog_mode_delivers_with_a_large_library(self):
        text = self.run_hook({'SKILLFORGE_HOOK': 'catalog'})
        self.assertTrue(text.startswith('# SkillForge catalog'), text[:80])
        self.assertLessEqual(len(text), 2400 * 4)

    def test_launcher_accepts_python_39(self):
        self.assertIn('(3, 9)', (ROOT / 'plugin/hooks/run-hook.sh').read_text())
        self.assertIn('(3, 9)', (ROOT / 'forge/py.mjs').read_text())


class NativeArm(unittest.TestCase):
    def test_every_module_becomes_a_registrable_skill(self):
        import ab
        with tempfile.TemporaryDirectory() as d:
            root = ab.native_plugin(Path(d))
            skills = sorted(root.glob('skills/*/SKILL.md'))
            self.assertEqual(len(skills), len([m for m in INDEX['modules'] if m['kind'] == 'module']))
            for p in skills:
                front = re.match(r'\A---\s*\n(.*?)\n---', p.read_text(encoding='utf-8'), re.S)
                self.assertTrue(front and re.search(r'^name:', front[1], re.M) and re.search(r'^description:', front[1], re.M), p)


class IsolatedAuth(unittest.TestCase):
    def test_paid_runs_need_a_credential_the_isolated_config_can_see(self):
        import ab
        from unittest import mock
        with mock.patch.object(ab, 'CREDS', Path(tempfile.gettempdir()) / 'no-such-credentials.json'), \
                mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(ab.isolated_auth_available())
            with mock.patch.dict(os.environ, {'CLAUDE_CODE_OAUTH_TOKEN': 'x'}):
                self.assertTrue(ab.isolated_auth_available())


class BenchmarkIntegrity(unittest.TestCase):
    def setUp(self):
        _, rules = library(INDEX, LIB, 'coding')
        self.ids = {r['id'] for r in rules}
        self.modules = {r['module'] for r in rules}

    def cases(self, path):
        return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]

    def test_every_label_matches_a_rule(self):
        from score_retrieval import check_labels
        files = sorted((ROOT / 'benchmarks/retrieval').glob('*.jsonl')) + [ROOT / 'benchmarks/heldout/cases.jsonl']
        for f in files:
            self.assertEqual(check_labels(self.cases(f), self.ids, self.modules, f.name), [], f.name)

    def test_label_checker_catches_a_dead_pattern(self):
        from score_retrieval import check_labels
        bad = [{'task': 'x', 'expect': ['postgres'], 'rules': [['systematic-debugging#*']]}]
        self.assertTrue(check_labels(bad, self.ids, self.modules, 'f'))

    def test_suite_sizes(self):
        sizes = {f.stem: len(self.cases(f)) for f in (ROOT / 'benchmarks/retrieval').glob('*.jsonl')}
        self.assertGreaterEqual(sum(1 for c in self.cases(ROOT / 'benchmarks/retrieval/dev.jsonl') if c['expect']), 100)
        for name, n in {'negatives': 50, 'ambiguous': 30, 'mixed': 30, 'security': 20, 'performance': 20}.items():
            self.assertGreaterEqual(sizes[name], n, name)

    def test_heldout_set_is_frozen(self):
        import hashlib
        digest = hashlib.sha256((ROOT / 'benchmarks/heldout/cases.jsonl').read_bytes()).hexdigest()
        self.assertIn(digest, (ROOT / 'benchmarks/heldout/README.md').read_text(encoding='utf-8'),
                      'the held-out set changed; it must not be edited after tuning')

    def test_every_task_has_a_scored_grader_and_solutions(self):
        tasks = sorted(p for p in (ROOT / 'benchmarks/tasks').iterdir() if p.is_dir())
        self.assertGreaterEqual(len(tasks), 30)
        for t in tasks:
            with self.subTest(task=t.name):
                test = (t / 'test.py').read_text(encoding='utf-8')
                self.assertRegex(test, r'SCORE:')
                self.assertTrue((t / 'task.txt').read_text(encoding='utf-8').strip())
                if t.name != 'react-waterfall':
                    spec = json.loads((ROOT / 'benchmarks/solutions' / t.name / 'variants.json').read_text(encoding='utf-8'))
                    self.assertTrue(any(v.get('expect') == 'pass' for v in spec['variants']))
                    self.assertTrue(any(v.get('must_fail') for v in spec['variants']))

    def test_task_graders_do_not_leak_into_solutions(self):
        for sol in (ROOT / 'benchmarks/solutions').iterdir():
            self.assertFalse(list(sol.rglob('test.py')), f'{sol.name}: a grader inside the solutions folder')


class ContextCost(unittest.TestCase):
    def test_runs_and_orders_arms_sensibly(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'cost.json'
            r = subprocess.run([sys.executable, str(ROOT / 'forge/context_cost.py'), '--json', str(out)],
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
        self.assertEqual(data['none']['mean_tokens'], 0)
        self.assertLess(data['sf-hook']['mean_tokens'], data['native']['mean_tokens'])


if __name__ == '__main__':
    unittest.main()
