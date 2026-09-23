"""Bounded delivery regression tests, without external model calls."""
import json, sys, tempfile, unittest
from pathlib import Path
from test_skillforge import mod, index, names
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin/skills/skillforge/scripts'))
import compose
from delivery import build_brief, catalog, tokens, terms, rank_rules


class Delivery(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'plugin/library'
        self.index = json.loads((self.root / 'index.json').read_text(encoding='utf-8'))

    def brief(self, tasks, **kwargs):
        return build_brief(self.index, self.root, 'coding', tasks, **kwargs)

    def test_symptom_routes_and_delivers_actual_rule(self):
        text, _, log = self.brief(['workers block each other in the queue'])
        self.assertIn('for update skip locked', text.lower())
        self.assertIn('postgres', log['delivered_modules'])
        self.assertNotIn('modules/postgres/MODULE.md', text)

    def test_stack_alone_does_not_select_modules(self):
        _, _, log = self.brief(['rewrite README wording'], stack=['react', 'postgres'])
        self.assertEqual(log['delivered_modules'], ['coding-core'])

    def test_exact_serialized_estimate_respects_budget(self):
        for budget in (350, 700, 1300, 2500):
            text, _, log = self.brief(['postgres query index table lock'], budget=budget)
            self.assertLessEqual(tokens(text), budget)
            self.assertEqual(tokens(text), log['estimated_output_tokens'])
            for u in log['units']:
                if u['result'] == 'delivered':
                    self.assertIn((self.root / u['path']).read_text(encoding='utf-8').strip(), text)

    def test_invalid_or_insufficient_budget_fails(self):
        for budget in (0, -1, 1):
            with self.assertRaises(ValueError): self.brief(['workers queue'], budget=budget)

    def test_new_rule_same_module_is_not_hidden_by_session(self):
        _, keys, _ = self.brief(['queue workers concurrency'])
        text, _, log = self.brief(['keyset cursor pagination'], emitted=keys)
        self.assertIn('data-pagination.md', text)
        self.assertIn('session hit', [u['result'] for u in log['units']])

    def test_repeated_brief_suppresses_bodies(self):
        first, keys, _ = self.brief(['queue workers concurrency'])
        second, _, log = self.brief(['queue workers concurrency'], emitted=keys)
        self.assertLess(len(second), len(first))
        self.assertTrue(all(u['result'] == 'session hit' for u in log['units']))

    def test_changed_content_invalidates_cache_without_version_bump(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); idx = index()
            (root / 'core.md').write_text('first', encoding='utf-8')
            _, keys, _ = build_brief(idx, root, 'coding', [])
            (root / 'core.md').write_text('second', encoding='utf-8')
            text, _, _ = build_brief(idx, root, 'coding', [], emitted=keys)
            self.assertIn('second', text)

    def test_delivery_ablation_keeps_selection_fixed(self):
        task = ['workers queue concurrency']
        _, _, rules = self.brief(task, delivery='rules')
        text, _, modules = self.brief(task, delivery='modules')
        self.assertEqual(rules['decisions'], modules['decisions'])
        self.assertIn('modules/postgres/MODULE.md', text)

    def test_catalog_excludes_scaffolding_and_aggregate_files(self):
        for r in catalog(self.index, self.root):
            self.assertFalse(Path(r['path']).name.startswith('_'))
            self.assertIn(Path(r['path']).parent.name, ('references', 'rules'))

    def test_no_cross_subtask_keyword_leak(self):
        _, _, log = self.brief(['workers queue concurrency', 'rewrite README wording'])
        self.assertIn('rewrite README wording', log['misses'])

    def test_dependency_cycles_refused(self):
        idx = index(mod('a', 100, ['bug'], requires=['b']), mod('b', 100, [], requires=['a']))
        self.assertEqual(names(compose.compose(idx, 'coding', ['bug'])), ['core'])

    def test_dependency_cannot_bypass_overlap_group(self):
        idx = index(mod('a', 100, ['bug'], group='same', requires=['b']), mod('b', 100, [], group='same'))
        self.assertEqual(names(compose.compose(idx, 'coding', ['bug'])), ['core'])

    def test_plural_is_one_signal_and_technology_does_not_pull_unrelated_rules(self):
        self.assertEqual(len(terms('workers')), 1)
        text, _, log = self.brief(['postgres cursor keyset pagination'])
        self.assertIn('data-pagination.md', text)
        self.assertNotIn('conn-pooling.md', text)
        self.assertNotIn('schema-foreign-key-indexes.md', text)

    def test_dependency_payload_must_fit_before_dependent_is_delivered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            idx = index(mod('parent', 1, ['bug'], requires=['dep']), mod('dep', 1, []))
            for name, body in [('core', 'core'), ('dep', 'long ' * 2000), ('parent', 'parent instructions')]:
                (root / f'{name}.md').write_text(body, encoding='utf-8')
            text, _, log = build_brief(idx, root, 'coding', ['bug'], budget=300)
            self.assertNotIn('parent instructions', text)
            self.assertIn('missing dependency payload', [u['result'] for u in log['units']])

    def test_path_traversal_refused(self):
        idx = index(); idx['modules'][0]['path'] = '../outside.md'
        with self.assertRaises(ValueError): build_brief(idx, self.root, 'coding', [])


if __name__ == '__main__': unittest.main()
