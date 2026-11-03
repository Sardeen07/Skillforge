"""Release checks for library metadata and ranking metrics."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'forge'))
from validate_library import validate
sys.path.insert(0, str(ROOT / 'forge'))
from score_retrieval import ndcg


class LibraryValidation(unittest.TestCase):
    def test_checked_in_library_has_valid_provenance_and_relations(self):
        index = json.loads((ROOT / 'plugin/library/index.json').read_text(encoding='utf-8'))
        count, refs, errors, warnings = validate(
            index, ROOT / 'plugin/library', ROOT / 'forge/curation/coding.json',
            ROOT / 'forge/curation/reference-domains.json')
        self.assertGreaterEqual(count, 500)
        self.assertGreaterEqual(len(refs), 400)
        self.assertEqual(errors, [])
        self.assertEqual({w.split(':')[0] for w in warnings}, {'linux-networking', 'ml-engineering'})

    def test_ndcg_rewards_correct_rules_earlier_and_handles_negative_cases(self):
        needs = [['a'], ['b']]
        self.assertGreater(ndcg(needs, ['a', 'x', 'b'], 3), ndcg(needs, ['x', 'a', 'b'], 3))
        self.assertEqual(ndcg([], [], 4), 1.0)
        self.assertEqual(ndcg([], ['unrelated/rule'], 4), 0.0)
