"""Runner integrity: activation evidence, isolation, and error accounting."""
import importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ab', ROOT / 'forge/ab.py')
ab = importlib.util.module_from_spec(spec); spec.loader.exec_module(ab)


def events(*blocks):
    return '\n'.join(json.dumps({'message': {'content': [b]}}) for b in blocks)


class BenchmarkIntegrity(unittest.TestCase):
    def test_prose_and_tool_arguments_do_not_prove_brief(self):
        out = events({'type': 'text', 'text': 'compose.py # SkillForge brief:'},
                     {'type': 'tool_use', 'id': '1', 'name': 'Bash',
                      'input': {'command': 'python compose.py --task "# SkillForge brief:"'}})
        active, brief, _ = ab.activation_events(out)
        self.assertTrue(active); self.assertFalse(brief)
        self.assertEqual(ab.activation_events(events({'type': 'text', 'text': 'compose.py'}))[:2], (False, False))

    def test_only_matching_successful_tool_result_proves_delivery(self):
        call = {'type': 'tool_use', 'id': 'a', 'name': 'Bash', 'input': {'command': 'python compose.py'}}
        result = {'type': 'tool_result', 'tool_use_id': 'a', 'content': '# SkillForge brief: coding\ntext'}
        self.assertTrue(ab.activation_events(events(call, result))[1])
        self.assertFalse(ab.activation_events(events(call, dict(result, is_error=True)))[1])
        self.assertFalse(ab.activation_events(events(call, dict(result, tool_use_id='other')))[1])

    def test_native_gets_exactly_eligible_modules(self):
        idx = json.loads((ROOT / 'plugin/library/index.json').read_text(encoding='utf-8'))
        want = {m['name'] for m in idx['modules'] if m['kind'] == 'module' and m['status'] in ('preferred', 'provisional')}
        with tempfile.TemporaryDirectory() as tmp:
            plugin = ab.native_plugin(Path(tmp))
            self.assertEqual({p.parent.name for p in plugin.glob('skills/*/SKILL.md')}, want)

    def test_fixture_excludes_hidden_grader_and_keeps_subdirectories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); dest = root / 'dest'; dest.mkdir()
            ab.setup('none', ROOT / 'benchmarks/tasks/react-waterfall', dest, root)
            self.assertFalse((dest / 'test.py').exists())
            self.assertTrue((dest / 'components').is_dir())

    def test_missing_cli_is_retained_as_unknown_cost_error(self):
        with patch.object(ab.subprocess, 'run', side_effect=FileNotFoundError('missing cli')):
            row = ab.run_one('none', ROOT / 'benchmarks/tasks/binary-search', 'task', 'Skill', 1, False, False)
        self.assertEqual(row['status'], 'harness_error')
        self.assertIsNone(row['cost']); self.assertIsNone(row['score'])

    def test_timeout_is_retained_as_error(self):
        with patch.object(ab.subprocess, 'run', side_effect=subprocess.TimeoutExpired('claude', 1)):
            row = ab.run_one('none', ROOT / 'benchmarks/tasks/binary-search', 'task', 'Skill', 1, False, False)
        self.assertEqual(row['status'], 'harness_error')
        self.assertIn('timed out', row['error'])

    def test_keep_never_retains_credential_support_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); dest = root / 'dest'; support = root / 'support'
            dest.mkdir(); support.mkdir()
            with patch.object(ab.tempfile, 'mkdtemp', side_effect=[str(dest), str(support)]):
                ab.run_one('none', ROOT / 'benchmarks/tasks/binary-search', 'task', 'Skill', 1, True, True)
            self.assertTrue(dest.exists()); self.assertFalse(support.exists())

    def test_grader_checks_are_recorded_individually(self):
        out = ('GRADER: v2 behavioral\nPASS  skip-locked          concurrent workers take distinct jobs\n'
               'FAIL  short-transaction    the job\'s row lock is still held while the payment call runs\n'
               'SCORE: 1/2\n')
        checks = ab.grade_checks(out)
        self.assertEqual([(c['name'], c['passed']) for c in checks], [('skip-locked', True), ('short-transaction', False)])
        self.assertIn('payment call', checks[1]['reason'])

    def test_skills_invoked_come_from_skill_tool_calls_only(self):
        out = events({'type': 'text', 'text': 'I will use the postgres skill'},
                     {'type': 'tool_use', 'id': '1', 'name': 'Skill', 'input': {'skill': 'postgres'}},
                     {'type': 'tool_use', 'id': '2', 'name': 'Bash', 'input': {'command': 'ls'}})
        self.assertEqual(ab.skills_invoked(out), ['postgres'])

    def test_attempt_is_saved_without_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); dest = root / 'dest'; support = root / 'support'; saved = root / 'saved'
            dest.mkdir(); support.mkdir()
            with patch.object(ab.tempfile, 'mkdtemp', side_effect=[str(dest), str(support)]), \
                 patch.object(ab.subprocess, 'run', side_effect=FileNotFoundError('missing cli')):
                row = ab.run_one('none', ROOT / 'benchmarks/tasks/binary-search', 'task', 'Skill', 1, False, False,
                                 save_to=saved)
            self.assertEqual(row['artifacts'], str(saved))
            self.assertTrue(any(saved.iterdir()))
            self.assertFalse(list(saved.rglob('.credentials.json')))
            self.assertFalse(dest.exists()); self.assertFalse(support.exists())

    def test_hook_evidence_comes_from_the_hook_log_only(self):
        log = chr(10).join(json.dumps(e) for e in [
            {'source': 'hook', 'units': [{'module': 'coding-core', 'result': 'delivered'},
                                         {'module': 'postgres', 'result': 'delivered'}]},
            {'source': 'hook', 'units': [{'module': 'coding-core', 'result': 'delivered'}]},  # core only
            {'source': 'hook', 'result': 'catalog delivered'},
            {'source': 'cli', 'units': [{'module': 'postgres', 'result': 'delivered'}]}])
        self.assertEqual(ab.hook_evidence(log + chr(10) + 'not json'), (1, 1))

    def test_rule_fetches_count_only_bash_calls(self):
        out = events({'type': 'tool_use', 'id': '1', 'name': 'Bash',
                      'input': {'command': 'python compose.py --rule postgres/lock-skip-locked'}},
                     {'type': 'text', 'text': 'compose.py --rule x'})
        self.assertEqual(ab.rule_fetches(out), 1)

    def test_arms_set_their_own_switches(self):
        self.assertEqual(ab.ARMS['sf-hook']['SKILLFORGE_HOOK'], 'brief')
        self.assertEqual(ab.ARMS['sf-catalog']['SKILLFORGE_HOOK'], 'catalog')
        self.assertEqual(ab.ARMS['skillforge']['SKILLFORGE_HOOK'], 'off', 'the skill arm must not get the hook')
        for arm in ab.ARMS.values():
            self.assertTrue(set(arm or {}) <= set(ab.SWITCHES), 'every switch must be cleared between arms')

    def test_crowd_is_installed_in_every_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); crowd = root / 'crowd'
            for name in ('alpha', 'beta'):
                (crowd / name).mkdir(parents=True)
                (crowd / name / 'SKILL.md').write_text('---' + chr(10) + 'name: x' + chr(10) + 'description: y' + chr(10) + '---' + chr(10), encoding='utf-8')
            for arm in ('none', 'native', 'sf-hook'):
                dest = root / arm; support = root / f'{arm}-support'
                dest.mkdir(); support.mkdir()
                extra = ab.setup(arm, ROOT / 'benchmarks/tasks/binary-search', dest, support, crowd)
                self.assertEqual(extra[:2], ['--plugin-dir', str(support / 'crowd-plugin')])
                self.assertEqual(len(list((support / 'crowd-plugin/skills').glob('*/SKILL.md'))), 2)
            with self.assertRaises(ValueError):
                (root / 'empty').mkdir(); ab.crowd_plugin(root / 'x', root / 'empty')

    def test_expert_arm_uses_the_task_selection_or_fails_loudly(self):
        rules = ab.expert_rules(ROOT / 'benchmarks/tasks/pg-queue-throughput')
        self.assertIn('postgres/lock-skip-locked', rules)
        with self.assertRaises(ValueError):
            ab.expert_rules(ROOT / 'benchmarks/tasks/binary-search')
        self.assertEqual(ab.ARMS['sf-expert']['SKILLFORGE_HOOK'], 'fixed')

    def test_expert_selection_is_outside_the_task_folder(self):
        for task in (ROOT / 'benchmarks/tasks').iterdir():
            self.assertFalse(list(task.rglob('expert*')), 'the agent under test would see it')
            self.assertFalse((task / 'solutions').exists(), 'the grader would read its .sql files')

    def test_crowds_combine_and_names_must_not_collide(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for crowd, name in (('unrelated', 'alpha'), ('similar', 'beta'), ('clash', 'alpha')):
                (root / crowd / name).mkdir(parents=True)
                (root / crowd / name / 'SKILL.md').write_text('x', encoding='utf-8')
            plugin = ab.crowd_plugin(root / 's1', [root / 'unrelated', root / 'similar'])
            self.assertEqual(sorted(p.name for p in (plugin / 'skills').iterdir()), ['alpha', 'beta'])
            with self.assertRaises(ValueError):
                ab.crowd_plugin(root / 's2', [root / 'unrelated', root / 'clash'])

    def test_dry_run_writes_no_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'results.jsonl'
            subprocess.run([sys.executable, str(ROOT / 'forge/ab.py'), '--dry-run', '--arms', 'sf-expert',
                            '--task', str(ROOT / 'benchmarks/tasks/binary-search'), '--output', str(out)],
                           capture_output=True, text=True)
            self.assertFalse(out.exists())
    def test_paid_expert_runs_need_a_reviewer(self):
        # The committed list was reviewed (Ali, 2026-09-23), so paid sf-expert runs are allowed.
        self.assertTrue(ab.expert_reviewed(ROOT / 'benchmarks/tasks/pg-queue-throughput'))
        # An unreviewed list must still block paid runs.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'demo.json').write_text('{"rules": [], "review": {"reviewed_by": null}}', encoding='utf-8')
            original, ab.EXPERT = ab.EXPERT, Path(tmp)
            try:
                self.assertFalse(ab.expert_reviewed(Path(tmp) / 'demo'))
            finally:
                ab.EXPERT = original

    def test_delivery_check_catches_missing_and_altered_rules(self):
        digests = ab.library_digests()
        good = [('postgres/lock-skip-locked', digests['postgres/lock-skip-locked'])]
        self.assertEqual(ab.check_delivery(good, digests, ['postgres/lock-skip-locked']), 'ok')
        self.assertIn('not delivered', ab.check_delivery(good, digests, ['postgres/data-pagination']))
        self.assertIn('altered', ab.check_delivery([('postgres/lock-skip-locked', 'x' * 64)], digests))

    def test_freeze_refuses_changed_conditions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'freeze.json'
            tasks = [ROOT / 'benchmarks/tasks/pg-queue-throughput']
            first = ab.manifest(tasks, 'model-a', 'Skill', None)
            self.assertEqual(ab.check_freeze(path, first), [])
            self.assertEqual(ab.check_freeze(path, first), [])
            self.assertEqual(ab.check_freeze(path, ab.manifest(tasks, 'model-b', 'Skill', None)), ['model'])
            self.assertEqual(first['tasks']['pg-queue-throughput']['grader_version'], 2)
            self.assertIsNotNone(first['hook_budget_tokens'])

    def test_grader_needing_postgres_is_detected(self):
        self.assertTrue(ab.needs_postgres(ROOT / 'benchmarks/tasks/pg-queue-throughput'))
        self.assertFalse(ab.needs_postgres(ROOT / 'benchmarks/tasks/binary-search'))

if __name__ == '__main__': unittest.main()
