"""Runner integrity: activation evidence, isolation, and error accounting."""
import importlib.util, json, subprocess, tempfile, unittest
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


if __name__ == '__main__': unittest.main()
