"""Regression checks for the approved HUMA ID-only migration.

Synthetic scripts and prompt contracts, not proof of native Agent execution.
No new lifecycle gate or implementation-acceptance capability is introduced.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'dist'
sys.path.insert(0, str(ROOT / 'tools'))
from localize import english_body
from naming import invocation, skill_id

HOSTS = ('codex', 'claude', 'cursor')
NEW = 'sdlc-210-huma'
OLD = 'sdlc-320-huma'
UNAPPROVED = 'sdlc-510-huma'


class HumaContractTests(unittest.TestCase):
    def test_huma_order_is_presentation_not_new_upstream_command(self):
        data = json.loads((ROOT / 'docs/naming-map.json').read_text())
        ids = [item['target_id'] for item in data['skills']]
        self.assertEqual(ids[4:8], ['sdlc-200-plan', NEW, 'sdlc-300-task', 'sdlc-310-xchk'])
        self.assertEqual(len(ids), 11)
        self.assertEqual(skill_id('checklist'), NEW)
        self.assertEqual(json.loads((ROOT/'upstream.lock.json').read_text())['commands'], [
            'constitution', 'specify', 'clarify', 'plan', 'tasks', 'analyze',
            'checklist', 'implement', 'converge',
        ])

    def test_all_hosts_load_210_and_reject_legacy_and_unapproved_ids(self):
        spec = importlib.util.spec_from_file_location('huma_loader', PACKAGE/'scripts/python/load_workflow.py')
        loader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loader)
        for host in HOSTS:
            with self.subTest(host=host):
                body = loader.load(PACKAGE, host, NEW)
                self.assertIn('需求写作的单元测试', body)
                self.assertIn('**不得**把新生成条目标为 `[x]`', body)
                self.assertIn('只有评审者明确要求时，Agent 才能协助评估条目', body)
                self.assertIn(invocation('specify', host), body)
                self.assertIn(invocation('clarify', host), body)
                self.assertIn(NEW, loader.load(PACKAGE, host, 'sdlc-400-impl'))
                for retired in (OLD, UNAPPROVED):
                    self.assertNotIn(retired, loader.SKILLS)
                    with self.assertRaises(ValueError):
                        loader.load(PACKAGE, host, retired)
                    self.assertFalse((PACKAGE/'skills'/retired).exists())
                    self.assertFalse((PACKAGE/'references/workflows'/(retired+'.md')).exists())

    def test_native_diagnostics_do_not_accept_legacy_or_510_aliases(self):
        for host in HOSTS:
            env = dict(os.environ, SDLC_HOST=host)
            for name in (NEW, OLD, UNAPPROVED):
                with self.subTest(host=host, name=name):
                    result = subprocess.run([
                        'bash', '-c', 'source "$1"; format_sdlc_command "$2"',
                        'huma-test', str(PACKAGE/'scripts/bash/common.sh'), name,
                    ], env=env, capture_output=True, text=True, timeout=10)
                    if name == NEW:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout.strip(), invocation('checklist', host))
                    else:
                        self.assertNotEqual(result.returncode, 0)

    def test_checklist_needs_plan_but_not_tasks_and_does_not_add_task_gate(self):
        for host in HOSTS:
            with self.subTest(host=host), tempfile.TemporaryDirectory(prefix='huma-context-') as temp:
                project = Path(temp)
                state = project/'.sdlc'
                feature = state/'specs/001-example'
                feature.mkdir(parents=True)
                (state/'init-options.json').write_text('{"script":"sh","feature_numbering":"sequential"}\n')
                (state/'feature.json').write_text('{"feature_directory":".sdlc/specs/001-example"}\n')
                (feature/'spec.md').write_text('# Synthetic specification\n')
                env = {k:v for k,v in os.environ.items() if not k.startswith(('SDLC_', 'SPECIFY_', 'PYTHON'))}
                env['SDLC_HOST'] = host
                command = ['bash', str(PACKAGE/'scripts/bash/check-prerequisites.sh'),
                           '--json', '--template', 'checklist-template']
                result = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(invocation('plan', host), result.stderr)
                (feature/'plan.md').write_text('# Synthetic plan\n')
                result = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(NEW, json.loads(result.stdout)['TEMPLATE_CONTENT'])
                self.assertFalse((feature/'tasks.md').exists())
                self.assertFalse((feature/'checklists').exists())
                # TASK's setup script keeps its original behavior, whether no
                # checklist exists or a reviewer-owned checklist is unchecked.
                setup = ['bash', str(PACKAGE/'scripts/bash/setup-tasks.sh'), '--json']
                for has_unchecked in (False, True):
                    if has_unchecked:
                        (feature/'checklists').mkdir()
                        (feature/'checklists/security.md').write_text('- [ ] CHK001 Are permission requirements defined?\n')
                    before = {str(p.relative_to(feature)): p.read_bytes() for p in feature.rglob('*') if p.is_file()}
                    result = subprocess.run(setup, cwd=project, env=env, capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for relative, data in before.items():
                        self.assertEqual((feature/relative).read_bytes(), data)

    def test_checklist_and_impl_ownership_contracts_are_preserved(self):
        for host in HOSTS:
            with self.subTest(host=host):
                checklist = english_body('checklist', host)
                for clause in (
                    'UNIT TESTS FOR REQUIREMENTS WRITING',
                    'NOT checking if code/implementation matches the spec',
                    'it MUST NOT mark generated items `[x]`',
                    'An agent may assist with evaluating items only when explicitly asked by the reviewer.',
                    'Never delete or replace existing checklist content - always preserve and append',
                ):
                    self.assertIn(clause, checklist)
                impl = english_body('implement', host)
                for clause in (
                    'do NOT modify checklist files or markers',
                    'Wait for user response before continuing',
                    'If user says "yes" or "proceed" or "continue", proceed to step 3',
                ):
                    self.assertIn(clause, impl)
                self.assertIn(invocation('checklist', host), impl)

    def test_convergence_does_not_become_a_huma_or_acceptance_stage(self):
        for host in HOSTS:
            with self.subTest(host=host):
                body = english_body('converge', host)
                self.assertIn('APPEND-ONLY, NEVER REWRITE', body)
                self.assertIn('recommend proceeding to review / opening a PR', body)
                self.assertIn('byte-for-byte unchanged', body)
                self.assertNotIn(invocation('checklist', host), body)

    def test_template_reference_uses_210_without_changing_checkboxes(self):
        template = (PACKAGE/'templates/checklist-template.md').read_text()
        self.assertEqual(template.count(NEW), 2)
        self.assertNotIn(OLD, template)
        self.assertIn('- [ ] CHK001', template)
        self.assertNotIn('- [x] CHK001', template)
        self.assertNotIn('- [X] CHK001', template)


if __name__ == '__main__':
    unittest.main()
