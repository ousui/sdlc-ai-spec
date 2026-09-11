"""Test approved naming documentation, NOT native host compatibility.

The source/target IDs are deliberately asserted independently from the README
renderer. Generator integration uses the same contract; these tests must not count
reserved skills as installed or approve unknown upstream names automatically.
See docs/NAMING.md and PR #24.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = (
    ('init', 'sdlc-000-init'),
    ('constitution', 'sdlc-010-rule'),
    ('specify', 'sdlc-100-spec'),
    ('clarify', 'sdlc-110-clar'),
    ('plan', 'sdlc-200-plan'),
    ('tasks', 'sdlc-300-task'),
    ('analyze', 'sdlc-310-xchk'),
    ('checklist', 'sdlc-320-huma'),
    ('implement', 'sdlc-400-impl'),
    ('converge', 'sdlc-500-conv'),
    (None, 'sdlc-status'),
)


class NamingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'docs/naming-map.json').read_text(encoding='utf-8'))
        cls.readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        cls.policy = (ROOT / 'docs/NAMING.md').read_text(encoding='utf-8')

    def test_exact_source_to_target_inventory(self):
        pairs = tuple((item['source_id'], item['target_id']) for item in self.data['skills'])
        self.assertEqual(pairs, EXPECTED)
        self.assertEqual(len({target for _, target in pairs}), len(pairs))

    def test_numbered_ids_are_ordered_four_letter_codes(self):
        stages = self.data['skills'][:-1]
        for item in stages:
            self.assertRegex(item['target_id'], r'^sdlc-[0-9]{3}-[a-z]{4}$')
        self.assertEqual([i['target_id'] for i in stages], sorted(i['target_id'] for i in stages))
        self.assertEqual([i['scope'] for i in stages[:2]], ['project', 'project'])
        self.assertTrue(all(i['scope'] == 'feature' for i in stages[2:]))

    def test_readme_table_has_every_name_and_meaning_exactly_once(self):
        rows = {}
        for line in self.readme.splitlines():
            if re.match(r'^\| `sdlc-', line):
                cells = [cell.strip() for cell in line.strip('|').split('|')]
                name = cells[0].strip('`')
                self.assertNotIn(name, rows)
                rows[name] = cells
        self.assertEqual(set(rows), {target for _, target in EXPECTED})
        for item in self.data['skills']:
            self.assertEqual(rows[item['target_id']][1:3], [item['english'], item['chinese']])

    def test_product_names_do_not_force_a_project_directory_rename(self):
        product = self.data['product']
        self.assertEqual(product['display_name'], 'SDLC AI SPEC')
        self.assertEqual(product['target_plugin_id'], 'sdlc-ai-spec')
        self.assertEqual(product['state_directory'], '.sdlc')
        self.assertEqual(product['code_prefix'], 'sdlc')
        self.assertEqual(product['environment_prefix'], 'SDLC_')

    def test_identifier_examples_match_the_approved_contexts(self):
        self.assertEqual(self.data['identifier_examples'], {
            'SPECIFY_INIT_DIR': 'SDLC_INIT_DIR',
            'SPECIFY_FEATURE': 'SDLC_FEATURE',
            'SPECIFY_FEATURE_DIRECTORY': 'SDLC_FEATURE_DIRECTORY',
            'find_specify_root': 'find_sdlc_root',
            'resolve_specify_init_dir': 'resolve_sdlc_init_dir',
        })
        for source, target in self.data['identifier_examples'].items():
            self.assertIn(source, self.policy)
            self.assertIn(target, self.policy)

    def test_provenance_and_existing_artifact_paths_are_preserved(self):
        self.assertEqual(set(self.data['preserve_paths']), {
            'src/upstream/', 'upstream.lock.json', 'LICENSE', 'NOTICE',
        })
        self.assertEqual(set(self.data['stable_artifact_paths']), {
            '.sdlc/specs/', 'spec.md', 'plan.md', 'tasks.md',
            'memory/constitution.md', 'checklists/requirements.md',
        })

    def test_status_is_local_utility_not_upstream_command(self):
        skills = self.data['skills']
        self.assertTrue(all(i['existing_capability'] is True for i in skills[:-1]))
        self.assertIs(skills[-1]['source_id'], None)
        self.assertIs(skills[-1]['existing_capability'], True)
        self.assertEqual(skills[-1]['local_id'], 'status')
        self.assertEqual(skills[-1]['scope'], 'utility')
        self.assertIn('状态与产物导航', self.readme)
        self.assertIn('已迁移生成入口', self.readme)
        self.assertEqual(self.data['status'], 'implemented-runtime-naming')

    def test_contract_links_and_work_package_boundary(self):
        self.assertIn('docs/NAMING.md', self.readme)
        self.assertIn('docs/naming-map.json', self.readme)
        self.assertIn('https://github.com/ousui/sdlc-ai-spec/pull/24', self.policy)
        self.assertEqual(set(self.data['deferred_behaviors']), {
            'rule-auto-initialization',
            'legacy-project-data-migration',
        })
        self.assertEqual(self.data['schema_version'], 1)


if __name__ == '__main__':
    unittest.main()
