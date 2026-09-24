"""Rule-level retrieval, bounded delivery, catalog and hook tests, without model calls."""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from test_skillforge import index
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugin/skills/skillforge/scripts'
sys.path.insert(0, str(SCRIPTS))
from delivery import build_brief, catalog_text, get_rules
from retrieval import Index, load_rules, split_sections, strip_frontmatter, terms, tokens

TASK = (ROOT / 'benchmarks/tasks/pg-queue-throughput/task.txt').read_text(encoding='utf-8')


class Delivery(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'plugin/library'
        self.index = json.loads((self.root / 'index.json').read_text(encoding='utf-8'))

    def brief(self, tasks, **kwargs):
        return build_brief(self.index, self.root, 'coding', tasks, **kwargs)

    def delivered(self, log):
        return [u['id'] for u in log['units'][1:] if u['result'] == 'delivered']

    def test_symptom_routes_and_delivers_actual_rule(self):
        text, _, log = self.brief(['workers block each other in the queue'])
        self.assertIn('for update skip locked', text.lower())
        self.assertIn('postgres/lock-skip-locked', self.delivered(log))
        self.assertNotIn('modules/postgres/MODULE.md', text)

    def test_benchmark_task_text_reaches_every_rule_it_names(self):
        """Regression: this paragraph used to route to four React rules and no Postgres."""
        text, _, log = self.brief([TASK], budget=2400, split=True, abstain_empty=True)
        got = self.delivered(log)
        for rule in ('postgres/lock-skip-locked', 'postgres/data-pagination', 'postgres/schema-foreign-key-indexes'):
            self.assertIn(rule, got)
        self.assertFalse([r for r in got if r.startswith('react-performance/')], got)
        self.assertLess(len(text), 10_000, 'Claude Code cuts hook context above 10,000 characters')

    def test_named_technology_outweighs_generic_words(self):
        _, _, log = self.brief(["listing a customer's orders on their account page takes seconds"],
                               stack=['postgres'])
        self.assertFalse([r for r in self.delivered(log) if r.startswith('react-performance/')])

    def test_technology_named_in_one_sentence_steers_the_others(self):
        _, _, log = self.brief(['Our app runs on Postgres. The report is unusable deep into its pages.'], split=True)
        self.assertTrue(self.delivered(log))
        self.assertFalse([r for r in self.delivered(log) if not r.startswith('postgres/')])

    def test_stack_alone_does_not_select_rules(self):
        _, _, log = self.brief(['rewrite README wording'], stack=['react', 'postgres'])
        self.assertEqual(log['delivered_modules'], ['coding-core'])
        self.assertEqual(log['misses'], ['rewrite README wording'])

    def test_generic_bug_fix_does_not_pull_in_a_whole_guide(self):
        text, _, _ = self.brief(['fix the bug'])
        self.assertLess(tokens(text), 1000, 'a generic request must not cost a 2,400-token procedure')

    def test_abstain_empty_returns_nothing_for_unrelated_prompt(self):
        text, keys, log = self.brief(['rewrite README wording'], abstain_empty=True)
        self.assertEqual(text, '')
        self.assertEqual(log['estimated_output_tokens'], 0)

    def test_exact_serialized_estimate_respects_budget(self):
        for budget in (350, 700, 1300, 2500):
            text, _, log = self.brief(['postgres query index table lock'], budget=budget)
            self.assertLessEqual(tokens(text), budget)
            self.assertEqual(tokens(text), log['estimated_output_tokens'])
            for u in log['units'][1:]:
                if u['result'] == 'delivered':
                    self.assertIn(u['id'], text)

    def test_invalid_or_insufficient_budget_fails(self):
        for budget in (0, -1, 1):
            with self.assertRaises(ValueError): self.brief(['workers queue'], budget=budget)

    def test_new_rule_same_module_is_not_hidden_by_session(self):
        _, keys, _ = self.brief(['queue workers concurrency skip locked'])
        text, _, log = self.brief(['keyset cursor pagination offset'], emitted=keys)
        self.assertIn('data-pagination', text)
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
        self.assertEqual(rules['parts'], modules['parts'])
        self.assertIn('modules/postgres/MODULE.md', text)

    def test_rules_exclude_scaffolding_and_aggregate_files(self):
        for r in load_rules(self.index, self.root):
            name = Path(r['path'].split('#')[0]).name
            self.assertFalse(name.startswith('_'), r['id'])
            self.assertNotIn(name, ('AGENTS.md', 'README.md', 'CHANGELOG.md'), r['id'])

    def test_no_cross_subtask_keyword_leak(self):
        _, _, log = self.brief(['workers queue concurrency', 'rewrite README wording'])
        self.assertIn('rewrite README wording', log['misses'])

    def test_one_normalizer_counts_plural_once(self):
        self.assertEqual(terms('workers'), ['worker'])
        self.assertEqual(set(terms('pages paging page')), {'pag'})
        text, _, _ = self.brief(['postgres cursor keyset pagination'])
        self.assertIn('data-pagination', text)
        self.assertNotIn('conn-pooling', text)

    def test_path_traversal_refused(self):
        idx = index(); idx['modules'][0]['path'] = '../outside.md'
        with self.assertRaises(ValueError): build_brief(idx, self.root, 'coding', [])


class ProceduralSections(unittest.TestCase):
    """Procedural guides are delivered a section at a time, with no text lost or edited."""

    def setUp(self):
        self.root = ROOT / 'plugin/library'
        self.index = json.loads((self.root / 'index.json').read_text(encoding='utf-8'))
        self.rules = load_rules(self.index, self.root)

    def test_guides_are_split_into_sections(self):
        debugging = [r for r in self.rules if r['module'] == 'systematic-debugging']
        self.assertGreater(len(debugging), 5)
        self.assertTrue(all(len(r['text']) < 4000 for r in debugging))
        self.assertEqual(len({r['id'] for r in self.rules}), len(self.rules), 'rule IDs must be unique')

    def test_sections_preserve_the_original_text(self):
        text = (self.root / 'modules/systematic-debugging/MODULE.md').read_text(encoding='utf-8')
        joined = ''.join(s for _, s in split_sections(text))
        squash = lambda t: ''.join(t.split())
        self.assertEqual(squash(joined), squash(strip_frontmatter(text)[1]))


class Catalog(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'plugin/library'
        self.index = json.loads((self.root / 'index.json').read_text(encoding='utf-8'))

    def test_catalog_lists_every_rule_under_the_hook_cap(self):
        text = catalog_text(self.index, self.root, 'coding', 'python compose.py')
        self.assertLess(len(text), 9600, 'the catalog is delivered by a hook; above 10,000 chars it is cut')
        for r in load_rules(self.index, self.root):
            self.assertIn(r['id'].split('/', 1)[1], text)

    def test_rules_fetch_by_id_and_unique_suffix(self):
        text, missing = get_rules(self.index, self.root, 'coding',
                                  ['postgres/lock-skip-locked', 'data-pagination', 'no-such-rule'])
        self.assertIn('SKIP LOCKED', text)
        self.assertIn('OFFSET', text)
        self.assertEqual(missing, ['no-such-rule'])

    def test_cli_rule_and_catalog(self):
        run = lambda *a: subprocess.run([sys.executable, str(SCRIPTS / 'compose.py'), *a], capture_output=True,
                                        text=True, encoding='utf-8', env={**os.environ, 'SKILLFORGE_LOG': os.devnull})
        self.assertTrue(run('--catalog').stdout.startswith('# SkillForge catalog: coding'))
        self.assertIn('SKIP LOCKED', run('--rule', 'postgres/lock-skip-locked').stdout)
        self.assertNotEqual(run('--rule', 'nope').returncode, 0)


class Hook(unittest.TestCase):
    """The hook is an experiment: off by default, bounded, silent when unsure, never blocking."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {**os.environ, 'SKILLFORGE_LOG': str(Path(self.tmp.name) / 'compose.log')}
        for name in ('SKILLFORGE_HOOK', 'SKILLFORGE_STACK', 'SKILLFORGE_DELIVERY', 'SKILLFORGE_RULES',
                     'SKILLFORGE_HOOK_BUDGET'):
            self.env.pop(name, None)

    def tearDown(self):
        self.tmp.cleanup()

    def run_hook(self, payload, mode='brief', **env):
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode('utf-8')
        extra = {'SKILLFORGE_HOOK': mode} if mode else {}
        r = subprocess.run([sys.executable, str(SCRIPTS / 'hook.py')], input=data, capture_output=True,
                           env={**self.env, **extra, **env}, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout.decode('utf-8').strip()
        return json.loads(out)['hookSpecificOutput']['additionalContext'] if out else ''

    def prompt(self, text, session='s1', cwd=None):
        return {'hook_event_name': 'UserPromptSubmit', 'session_id': session, 'prompt': text,
                'cwd': cwd or self.tmp.name}

    def last_log(self):
        lines = (Path(self.tmp.name) / 'compose.log').read_text(encoding='utf-8').splitlines()
        return json.loads(lines[-1])

    def test_off_by_default(self):
        self.assertEqual(self.run_hook(self.prompt(TASK), mode=None), '')

    def test_injects_brief_for_the_raw_prompt(self):
        text = self.run_hook(self.prompt(TASK))
        self.assertTrue(text.startswith('# SkillForge brief:'))
        self.assertIn('postgres/lock-skip-locked', text)
        self.assertLess(len(text), 9600)

    def test_budget_is_configurable(self):
        text = self.run_hook(self.prompt(TASK), SKILLFORGE_HOOK_BUDGET='800')
        self.assertLessEqual(len(text), 3200)

    def test_silent_for_unrelated_prompt_off_switch_and_slash_commands(self):
        self.assertEqual(self.run_hook(self.prompt('rewrite the README wording')), '')
        self.assertEqual(self.run_hook(self.prompt(TASK), mode='off'), '')
        self.assertEqual(self.run_hook(self.prompt('/forge-status')), '')

    def test_follow_ups_add_nothing(self):
        """Earlier rules are still in context; a follow-up has no new evidence to rank."""
        for text in ('continue', 'fix that', 'ok do it', 'yes'):
            self.assertEqual(self.run_hook(self.prompt(text, session='f1')), '', text)

    def test_detects_the_project_stack(self):
        fixture = str(ROOT / 'benchmarks/tasks/pg-queue-throughput')
        self.run_hook(self.prompt('workers wait on each other in the job queue', cwd=fixture))
        log = self.last_log()
        self.assertEqual((log['stack'], log['stack_source']), (['postgres'], 'detected'))
        self.run_hook(self.prompt('workers wait on each other in the job queue', 's2', cwd=fixture),
                      SKILLFORGE_STACK='react')
        self.assertEqual(self.last_log()['stack'], ['react'], 'an explicit stack wins')

    def test_session_cache_and_compaction_reset(self):
        self.assertTrue(self.run_hook(self.prompt(TASK)))
        self.assertEqual(self.run_hook(self.prompt(TASK)), '', 'already delivered this session')
        self.run_hook({'hook_event_name': 'SessionStart', 'session_id': 's1', 'source': 'compact'})
        self.assertTrue(self.run_hook(self.prompt(TASK)), 'compaction dropped it from context')

    def test_catalog_mode_once_per_session(self):
        first = self.run_hook(self.prompt('hello', 'c1'), mode='catalog')
        self.assertTrue(first.startswith('# SkillForge catalog:'))
        self.assertEqual(self.run_hook(self.prompt('again', 'c1'), mode='catalog'), '')

    def test_fixed_mode_delivers_exactly_the_selected_rules(self):
        rules = 'postgres/data-pagination,postgres/lock-skip-locked'
        text = self.run_hook(self.prompt('anything at all', 'x1'), mode='fixed', SKILLFORGE_RULES=rules)
        self.assertIn('postgres/data-pagination', text)
        self.assertIn('postgres/lock-skip-locked', text)
        self.assertNotIn('postgres/schema-foreign-key-indexes', text)
        self.assertEqual(self.run_hook(self.prompt('again', 'x1'), mode='fixed', SKILLFORGE_RULES=rules), '')

    def test_bad_input_never_blocks(self):
        self.assertEqual(self.run_hook(b'not json'), '')
        self.assertEqual(self.run_hook(self.prompt('x'), mode='fixed', SKILLFORGE_RULES='no/such-rule'), '')

    def test_plugin_registers_the_hook(self):
        cfg = json.loads((ROOT / 'plugin/hooks/hooks.json').read_text(encoding='utf-8'))
        commands = [h['command'] for group in cfg['hooks']['UserPromptSubmit'] for h in group['hooks']]
        self.assertTrue(any('run-hook.sh' in c for c in commands))
        self.assertIn('SKILLFORGE_HOOK:-off', (ROOT / 'plugin/hooks/run-hook.sh').read_text(encoding='utf-8'))


class Relations(unittest.TestCase):
    """Procedural steps arrive with the steps they depend on, or not at all."""

    def setUp(self):
        self.root = ROOT / 'plugin/library'
        self.index = json.loads((self.root / 'index.json').read_text(encoding='utf-8'))

    def delivered(self, log):
        return [u['id'] for u in log['units'][1:] if u['result'] == 'delivered']

    def test_a_late_step_brings_its_earlier_steps_in_order(self):
        _, _, log = build_brief(self.index, self.root, 'coding', [],
                                rule_ids=['systematic-debugging/phase-4-implementation'])
        steps = ['systematic-debugging/overview', 'systematic-debugging/phase-1-root-cause-investigation',
                 'systematic-debugging/phase-2-pattern-analysis',
                 'systematic-debugging/phase-3-hypothesis-and-testing',
                 'systematic-debugging/phase-4-implementation']
        self.assertEqual(self.delivered(log), steps)
        self.assertEqual([u['required_by'] for u in log['units'][1:5]],
                         ['systematic-debugging/phase-4-implementation'] * 4)

    def test_dependencies_that_do_not_fit_block_the_rule(self):
        _, _, log = build_brief(self.index, self.root, 'coding', [], budget=900,
                                rule_ids=['systematic-debugging/phase-4-implementation'])
        self.assertEqual(self.delivered(log), [])
        self.assertTrue(all(u['result'] == 'over budget (with its dependencies)' for u in log['units'][1:]))

    def test_dependencies_already_in_context_are_not_resent(self):
        _, keys, _ = build_brief(self.index, self.root, 'coding', [],
                                 rule_ids=['systematic-debugging/phase-1-root-cause-investigation'])
        _, _, log = build_brief(self.index, self.root, 'coding', [], emitted=keys,
                                rule_ids=['systematic-debugging/phase-2-pattern-analysis'])
        self.assertEqual(self.delivered(log), ['systematic-debugging/phase-2-pattern-analysis'])

    def test_conflicting_rules_are_refused(self):
        idx = json.loads(json.dumps(self.index))
        pg = next(m for m in idx['modules'] if m['name'] == 'postgres')
        pg['rules'] = {'data-pagination': {'conflicts': ['lock-skip-locked']}}
        _, _, log = build_brief(idx, self.root, 'coding', [],
                                rule_ids=['postgres/lock-skip-locked', 'postgres/data-pagination'])
        self.assertEqual(self.delivered(log), ['postgres/lock-skip-locked'])
        self.assertIn('refused: conflicts', log['units'][-1]['result'])

    def test_cycles_and_unknown_names_are_errors(self):
        idx = json.loads(json.dumps(self.index))
        pg = next(m for m in idx['modules'] if m['name'] == 'postgres')
        pg['rules'] = {'data-pagination': {'requires': ['lock-skip-locked']},
                       'lock-skip-locked': {'requires': ['data-pagination']}}
        with self.assertRaises(ValueError):
            build_brief(idx, self.root, 'coding', [], rule_ids=['postgres/data-pagination'])
        pg['rules'] = {'data-pagination': {'requires': ['no-such-rule']}}
        with self.assertRaises(ValueError):
            load_rules(idx, self.root)

    def test_every_rule_reports_its_evidence_status(self):
        text, _, _ = build_brief(self.index, self.root, 'coding', [], rule_ids=['postgres/lock-skip-locked'])
        self.assertIn('Evidence: untested', text)


class Ambiguity(unittest.TestCase):
    def test_split_evidence_abstains(self):
        root = ROOT / 'plugin/library'
        index = json.loads((root / 'index.json').read_text(encoding='utf-8'))
        task = 'the same user lookup runs four times while rendering one page'
        _, _, log = build_brief(index, root, 'coding', [task])
        self.assertEqual(log['misses'], [task])


class GraderValidation(unittest.TestCase):
    """A grader must pass correct solutions and fail broken ones on the relevant checks.
    Static mode here (fast); `npm run graders` also validates the behavioral mode."""

    def test_graders_agree_with_reference_solutions(self):
        sys.path.insert(0, str(ROOT / 'forge'))
        import validate_graders
        for task in sorted(p.name for p in (ROOT / 'benchmarks/solutions').iterdir() if p.is_dir()):
            for row in validate_graders.validate(task, modes=('static',)):
                with self.subTest(task=task, variant=row['variant']):
                    self.assertTrue(row['ok'], row)

    def test_overlapping_failures_are_allowed_but_full_marks_are_not(self):
        sys.path.insert(0, str(ROOT / 'forge'))
        from validate_graders import judge
        spec = {'must_fail': ['a'], 'must_pass': ['c']}
        self.assertTrue(judge(spec, {'score': '1/3', 'full': False, 'failed': ['a', 'b'], 'passed': ['c']})[0])
        self.assertFalse(judge(spec, {'score': '2/3', 'full': False, 'failed': ['b'], 'passed': ['a', 'c']})[0])
        self.assertFalse(judge({'expect': 'pass'}, {'score': '2/3', 'full': False, 'failed': ['a'], 'passed': []})[0])

class SessionState(unittest.TestCase):
    """Previously delivered is not the same as still available."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {**os.environ, 'SKILLFORGE_LOG': str(Path(self.tmp.name) / 'compose.log'),
                    'SKILLFORGE_HOOK': 'brief'}
        for name in ('SKILLFORGE_STACK', 'SKILLFORGE_DELIVERY', 'SKILLFORGE_RULES', 'SKILLFORGE_HOOK_BUDGET'):
            self.env.pop(name, None)

    def tearDown(self):
        self.tmp.cleanup()

    def send(self, payload):
        payload = {'session_id': 'st', 'cwd': self.tmp.name, **payload}
        r = subprocess.run([sys.executable, str(SCRIPTS / 'hook.py')], input=json.dumps(payload).encode('utf-8'),
                           capture_output=True, env=self.env, timeout=60)
        out = r.stdout.decode('utf-8').strip()
        return json.loads(out)['hookSpecificOutput']['additionalContext'] if out else ''

    def prompt(self, text):
        return self.send({'hook_event_name': 'UserPromptSubmit', 'prompt': text})

    def start(self, source):
        self.send({'hook_event_name': 'SessionStart', 'source': source})

    def last_session(self):
        lines = (Path(self.tmp.name) / 'compose.log').read_text(encoding='utf-8').splitlines()
        return json.loads(lines[-1])['session']

    def test_follow_up_with_context_intact_adds_nothing(self):
        self.assertTrue(self.prompt(TASK))
        self.assertEqual(self.prompt('continue'), '')
        self.assertEqual(self.last_session()['action'], 'follow-up: nothing new')

    def test_follow_up_after_compaction_restores_the_last_rules(self):
        self.assertIn('postgres/lock-skip-locked', self.prompt(TASK))
        self.start('compact')
        restored = self.prompt('continue')
        self.assertIn('postgres/lock-skip-locked', restored)
        self.assertEqual(self.last_session()['action'], 'restored after compact')
        self.assertEqual(self.prompt('keep going'), '', 'restored once, then intact again')

    def test_resume_is_treated_as_possibly_lost(self):
        self.prompt(TASK)
        self.start('resume')
        self.assertIn('postgres/lock-skip-locked', self.prompt('ok do it'))

    def test_a_new_task_drops_the_old_rules(self):
        self.prompt(TASK)
        self.start('compact')
        self.assertEqual(self.prompt('rewrite the README wording for the release notes'), '')
        self.assertEqual(self.last_session()['active_rules'], [])
        self.assertEqual(self.prompt('continue'), '', 'stale rules from the old task must not come back')

    def test_a_changed_task_restores_the_new_task_rules_not_the_old(self):
        self.prompt(TASK)
        self.prompt('the page waits for one fetch to finish before starting the next')
        self.start('compact')
        restored = self.prompt('continue')
        self.assertNotIn('postgres/lock-skip-locked', restored)
        self.assertIn('react-performance/', restored)

    def test_clear_starts_over(self):
        self.prompt(TASK)
        self.start('clear')
        self.assertEqual(self.prompt('continue'), '')
        self.assertTrue(self.prompt(TASK), 'nothing counts as delivered after /clear')


class MixedTechnologies(unittest.TestCase):
    """Ambiguous prompts abstain; explicitly mixed ones get guidance for each technology."""

    def setUp(self):
        self.root = ROOT / 'plugin/library'
        self.index = json.loads((self.root / 'index.json').read_text(encoding='utf-8'))

    def modules(self, text):
        _, _, log = build_brief(self.index, self.root, 'coding', [text], split=True)
        return {u['module'] for u in log['units'][1:] if u['result'] == 'delivered'}

    def test_framework_names_with_dot_js_are_technologies(self):
        self.assertEqual(terms('Next.js'), terms('nextjs'))

    def test_two_sentences_two_technologies(self):
        got = self.modules('Our Next.js page awaits each fetch in sequence. '
                           'Separately, deleting a customer in Postgres scans the whole orders table.')
        self.assertEqual(got, {'react-performance', 'postgres'})

    def test_one_sentence_naming_both_gets_both(self):
        got = self.modules('Fix the React request waterfall and the Postgres pagination query.')
        self.assertEqual(got, {'react-performance', 'postgres'})

    def test_ambiguous_symptom_still_abstains(self):
        self.assertEqual(self.modules('the same user lookup runs four times while rendering one page'), set())


if __name__ == '__main__': unittest.main()
