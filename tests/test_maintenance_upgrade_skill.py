"""Repository-maintenance Skill contract; never part of the installed 11-Skill product."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build import ALL_COMMANDS, build
from naming import skill_id

SKILL_DIR = ROOT / '.agents/skills/sdlc-maintain-upgrade'
SKILL = SKILL_DIR / 'SKILL.md'
CLAUDE_ADAPTER = ROOT / '.claude/commands/sdlc-maintain-upgrade.md'
OPENAI_META = SKILL_DIR / 'agents/openai.yaml'


def split_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding='utf-8')
    match = re.match(r'\A---\n(.*?)\n---\n(.*)\Z', text, re.S)
    if not match:
        raise AssertionError(f'missing frontmatter: {path}')
    meta = yaml.safe_load(match[1])
    if not isinstance(meta, dict):
        raise AssertionError(f'invalid frontmatter: {path}')
    return meta, match[2]


class MaintenanceUpgradeSkillTests(unittest.TestCase):
    def test_one_canonical_skill_and_thin_claude_adapter(self):
        meta, body = split_frontmatter(SKILL)
        self.assertEqual(meta['name'], 'sdlc-maintain-upgrade')
        self.assertTrue(meta['disable-model-invocation'])
        self.assertIn('SDLC AI SPEC source repository itself', body)

        claude_meta, claude_body = split_frontmatter(CLAUDE_ADAPTER)
        self.assertTrue(claude_meta['disable-model-invocation'])
        self.assertIn('.agents/skills/sdlc-maintain-upgrade/SKILL.md', claude_body)
        self.assertIn('$ARGUMENTS', claude_body)
        self.assertNotIn('tools/upgrade.py prepare', claude_body)

        # Do not create duplicate repository-level copies that Cursor would also discover.
        for path in (
            ROOT / '.cursor/skills/sdlc-maintain-upgrade/SKILL.md',
            ROOT / '.codex/skills/sdlc-maintain-upgrade/SKILL.md',
            ROOT / '.claude/skills/sdlc-maintain-upgrade/SKILL.md',
            ROOT / 'maintenance/skills/sdlc-maintain-upgrade/SKILL.md',
        ):
            self.assertFalse(path.exists(), str(path))

    def test_codex_policy_is_explicit_only_and_name_is_canonical(self):
        data = yaml.safe_load(OPENAI_META.read_text(encoding='utf-8'))
        self.assertEqual(data['interface']['display_name'], 'sdlc-maintain-upgrade')
        self.assertEqual(data['policy']['allow_implicit_invocation'], False)

    def test_product_distribution_stays_exactly_eleven_skills(self):
        expected = {skill_id(name) for name in ALL_COMMANDS}
        actual = {p.parent.name for p in (ROOT / 'dist/skills').glob('*/SKILL.md')}
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 11)
        self.assertNotIn('sdlc-maintain-upgrade', actual)
        self.assertFalse((ROOT / 'dist/skills/sdlc-maintain-upgrade').exists())

    def test_maintenance_files_never_enter_generated_distribution(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'dist'
            build(out)
            names = {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()}
            self.assertFalse(any('sdlc-maintain-upgrade' in name for name in names))
            self.assertFalse(any(name.startswith('maintenance/') for name in names))

    def test_skill_orchestrates_existing_tools_in_required_order(self):
        text = SKILL.read_text(encoding='utf-8')
        for item in (
            'tools/upgrade.py prepare',
            'tools/localize.py export',
            'tools/localize.py precheck',
            'tools/localize.py record',
            'tools/localize.py check',
            'tools/upgrade.py refresh-localization',
            'tools/verify.py',
        ):
            self.assertIn(item, text)
        stages = [
            '## 4. Generate the detached candidate',
            '## 5. Incremental localization recovery',
            '## 6. Create independent target baselines',
            '## 7. Verify the exact candidate',
            '## 8. Default final report and stop boundary',
        ]
        positions = [text.index(item) for item in stages]
        self.assertEqual(positions, sorted(positions))

    def test_default_stop_boundary_prevents_release_effects(self):
        text = SKILL.read_text(encoding='utf-8')
        for phrase in (
            'Do not call formal `upgrade.py accept`',
            'commit the candidate',
            'push, merge, tag, release',
            'Default terminal state',
            '`VERIFIED_CANDIDATE_READY`',
            'Stop here unless the user separately authorizes',
        ):
            self.assertIn(phrase, text)

    def test_localization_write_scope_and_no_checker_weakening_are_explicit(self):
        text = SKILL.read_text(encoding='utf-8')
        self.assertIn('<CANDIDATE>/src/locales/zh-CN/**', text)
        self.assertIn('Do not edit candidate `tools/`, tests, adapters, upstream source', text)
        self.assertIn('never edit the checker or exception policy inside the upgrade run', text)
        self.assertIn('Do not make the upgrade pass by weakening checks', text)
        self.assertIn('do not call it independent-model evidence', text)
        self.assertIn('never reuse an older `User-approved` identity', text)

    def test_structural_changes_and_unknown_aliases_fail_closed(self):
        text = SKILL.read_text(encoding='utf-8')
        self.assertIn('core command added, removed, renamed, or re-scoped', text)
        self.assertIn('new or changed machine identifiers', text)
        self.assertIn('Do not invent new `structural_aliases` or input aliases', text)
        self.assertGreaterEqual(text.count('`REVIEW_REQUIRED`'), 5)

    def test_business_projects_are_out_of_scope(self):
        text = SKILL.read_text(encoding='utf-8')
        self.assertIn('must never be used to upgrade a business project', text)
        self.assertIn('Do not read or modify real business project `.sdlc` data', text)

    def test_supporting_references_and_flow_are_present(self):
        for relative in (
            'references/review-checklist.md',
            'references/report-template.md',
        ):
            self.assertTrue((SKILL_DIR / relative).is_file(), relative)
        flow = (ROOT / 'maintenance/UPGRADE-FLOW.html').read_text(encoding='utf-8')
        self.assertIn('sdlc-maintain-upgrade', flow)
        self.assertNotRegex(flow, r'(?<!maintain-)sdlc-upgrade\b')

    def test_repository_metadata_does_not_advertise_maintenance_skill_as_product(self):
        metadata = json.loads((ROOT / 'plugin-metadata.json').read_text(encoding='utf-8'))
        self.assertNotIn('sdlc-maintain-upgrade', json.dumps(metadata, ensure_ascii=False))
        for path in (
            ROOT / '.agents/plugins/marketplace.json',
            ROOT / '.claude-plugin/marketplace.json',
            ROOT / '.cursor-plugin/marketplace.json',
        ):
            self.assertNotIn('sdlc-maintain-upgrade', path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
