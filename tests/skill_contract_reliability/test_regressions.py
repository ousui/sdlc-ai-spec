"""Independent SCR oracles fixed from the original failures before implementation.

These are reconstructed protocol cases, not approval-bot's unavailable original
snapshot and not a new-context model experiment. Existing business oracles remain
unchanged; the RLS regression forces the previously timing-dependent collision.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.skills import test_sdlc_000_ctx as ctx
from tests.skill_rls import final_support as rls
from packages.sdlc_runtime import EnvelopeValidationError, validate_invocation

ROOT = Path(__file__).resolve().parents[2]


def snapshot(root: Path) -> dict[str, tuple[str, int]]:
    return {str(p.relative_to(root)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()}


class CtxContractRegressions(unittest.TestCase):
    def setUp(self):
        self.fixture = ctx.CtxRuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.project_root

    def invalid_type(self, dry_run=False):
        value = self.fixture.invocation(dry_run=dry_run)
        value['inputs']['context']['resources'][0]['type'] = 'source_worktree'
        return value

    def assert_refused_without_artifact(self, value):
        before = snapshot(self.root)
        result = self.fixture.invoke(value)
        self.assertFalse(result['ok'], result)
        self.assertEqual('failed', result['status'], result)
        self.assertEqual({'result': 'pending', 'failed_checks': []}, result['gate'])
        self.assertTrue(result['errors'], result)
        self.assertIsNone(result['artifact'])
        self.assertEqual(before, snapshot(self.root))
        self.assertFalse((self.root / '.sdlc').exists())
        return result

    def test_scr_e02_invalid_enum_does_not_fabricate_fifteen_failures(self):
        self.assert_refused_without_artifact(self.invalid_type())

    def test_scr_e07_create_dry_run_preserves_builder_errors(self):
        normal = self.assert_refused_without_artifact(self.invalid_type())
        preview = self.assert_refused_without_artifact(self.invalid_type(True))
        self.assertEqual(normal['errors'], preview['errors'])

    def test_scr_e07_builder_marks_unexecuted_checks_pending(self):
        value = self.invalid_type(True)
        product = ctx.runtime.build_payload(value, artifact_id='CTX-00000000000000-00',
                                            revision=1, base_revision=None, now=ctx.FIXED_TIME)
        self.assertTrue(product.errors)
        self.assertEqual('pending', product.gate_result)
        self.assertEqual([], product.failed_checks)

    def test_scr_e01_legacy_minimal_pair_still_previews_without_authority(self):
        before = snapshot(self.root)
        result = self.fixture.invoke(self.fixture.invocation(dry_run=True))
        self.assertTrue(result['ok'], result)
        self.assertEqual('pending', result['gate']['result'])
        self.assertFalse(result['errors'])
        self.assertIsNone(result['artifact'])
        self.assertEqual(before, snapshot(self.root))

    def test_scr_e06_observation_time_is_not_a_versioned_baseline(self):
        for baseline in ('workspace observation at 2026-09-08T01:00:00+08:00',
                         '2026-09-08T01:00:00+08:00', 'git:HEAD', 'vcs:repo@main', 'latest', 'None'):
            with self.subTest(baseline=baseline):
                value = self.fixture.invocation(dry_run=True)
                value['inputs']['context']['resources'][0]['baseline_reference'] = baseline
                result = self.assert_refused_without_artifact(value)
                self.assertIn('baseline', json.dumps(result['errors']).lower())

    def test_scr_e06_legacy_vcs_and_content_digest_have_distinct_supported_forms(self):
        for baseline in ('vcs:example@0123456789abcdef', 'vcs:repo@' + 'a' * 40,
                         'git:' + 'b' * 40, 'snapshot.txt@sha256:' + 'c' * 64):
            with self.subTest(baseline=baseline):
                value = self.fixture.invocation(dry_run=True)
                value['inputs']['context']['resources'][0]['baseline_reference'] = baseline
                result = self.fixture.invoke(value)
                self.assertTrue(result['ok'], result)
                self.assertEqual('pending', result['gate']['result'])
                self.assertIsNone(result['artifact'])
                self.assertFalse((self.root / '.sdlc').exists())

    def test_scr_e07_revise_invalid_input_preserves_frozen_revision_and_authority(self):
        reference, _ = self.fixture.create_and_freeze()
        before = snapshot(self.root)
        value = self.invalid_type()
        value.update(operation='revise', artifact_reference=reference)
        value['inputs']['refresh'] = self.fixture.refresh(1, changes=[reference + '#RSC-001'])
        for dry in (False, True):
            with self.subTest(dry_run=dry):
                value['options']['dry_run'] = dry
                result = self.fixture.invoke(value)
                self.assertFalse(result['ok'], result)
                self.assertEqual({'result': 'pending', 'failed_checks': []}, result['gate'])
                self.assertTrue(result['errors'])
                self.assertEqual(before, snapshot(self.root))
        check = self.fixture.invoke(self.fixture.invocation('check', reference=reference))
        self.assertTrue(check['ok'], check)
        self.assertEqual('frozen', check['artifact']['revision_state'])

    def test_scr_e18_unhashable_operation_returns_a_structured_error(self):
        for operation in ([], {}, ['create']):
            with self.subTest(operation=operation):
                value = self.fixture.invocation(dry_run=True)
                value['operation'] = operation
                result = self.fixture.invoke(value)
                self.assertFalse(result['ok'])
                self.assertEqual('INVALID_ENVELOPE', result['errors'][0]['code'])
                self.assertFalse((self.root / '.sdlc').exists())


class MetaCommandRegressions(unittest.TestCase):
    def probe(self, phase, *, open_stdin):
        with tempfile.TemporaryDirectory(prefix='scr-meta-') as directory:
            root = Path(directory)
            script = ROOT / 'skills' / ('sdlc-' + phase) / 'scripts/runtime.py'
            for command in ('help', 'version', 'commands', 'examples', '--help', '-V'):
                with self.subTest(phase=phase, command=command, open_stdin=open_stdin):
                    process = subprocess.Popen([sys.executable, '-B', str(script), command, '--output', 'json'],
                                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                               cwd=root, text=True,
                                               env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
                    try:
                        if open_stdin:
                            try:
                                process.wait(timeout=3)
                            except subprocess.TimeoutExpired:
                                self.fail('meta command consumed non-terminating business stdin')
                            process.stdin.close(); process.stdin = None
                            stdout, stderr = process.communicate(timeout=3)
                        else:
                            stdout, stderr = process.communicate('{invalid business JSON', timeout=8)
                        self.assertEqual(0, process.returncode, (stdout, stderr))
                        result = json.loads(stdout)
                        self.assertTrue(result['ok'], result)
                        self.assertEqual('meta', result['state'])
                        self.assertEqual([], result['effects'])
                        self.assertEqual([], list(root.iterdir()))
                    finally:
                        if process.poll() is None:
                            process.kill()
                        process.communicate()

    def test_scr_e12_dsn_invalid_stdin_is_ignored(self): self.probe('200-dsn', open_stdin=False)
    def test_scr_e12_pln_invalid_stdin_is_ignored(self): self.probe('300-pln', open_stdin=False)
    def test_scr_e12_dsn_nonterminating_stdin_is_not_consumed(self): self.probe('200-dsn', open_stdin=True)
    def test_scr_e12_pln_nonterminating_stdin_is_not_consumed(self): self.probe('300-pln', open_stdin=True)


class EnvelopeTypeRegressions(unittest.TestCase):
    def test_scr_e18_operation_type_is_validated_before_membership(self):
        for operation in ([], {}, True, 1):
            with self.subTest(operation=operation):
                with self.assertRaises(EnvelopeValidationError):
                    validate_invocation({'contract': 'sdlc-ai-spec/runtime-invocation/v1',
                                         'operation': operation, 'project_root': '/fixture/project', 'inputs': {}})


class RlsTargetIdentityRegression(rls.FinalRlsCase):
    def test_scr_e29_target_switch_allocates_even_when_provisional_id_collides(self):
        self.create()
        old_state, old_generation = self.service.read(self.reference)
        original_target = snapshot(self.target.root)
        with tempfile.TemporaryDirectory(prefix='scr-new-target-') as directory:
            other = rls.SandboxReleaseTarget(directory, 'sandbox-b')
            with patch('rls_builder._artifact_id', return_value=self.state['artifact']['id']):
                state, _ = self.service.revise(self.reference, self.chain['vfy'], other)
            self.assertNotEqual(self.state['artifact']['id'], state['artifact']['id'])
            self.assertEqual('sandbox-b', state['release_contract']['release_target'])
            self.assertEqual(str(other.root), state['release_contract']['target_locator'])
            self.assertIsNone(state['effect_authorization'])
            self.assertFalse(state['target_effect'])
            self.assertEqual([], list(Path(directory).iterdir()))
        current, generation = self.service.read(self.reference)
        self.assertEqual(old_state, current)
        self.assertEqual(old_generation, generation)
        self.assertEqual(original_target, snapshot(self.target.root))

    def test_scr_e29_same_target_no_change_preserves_generation_and_store(self):
        self.create()
        before = snapshot(self.root)
        state, generation = self.service.revise(self.reference, self.chain['vfy'], self.target)
        self.assertEqual(self.reference, state['artifact']['reference'])
        self.assertIsNone(generation)
        self.assertIn('RLS_NO_CHANGE', state['warnings'])
        self.assertEqual(before, snapshot(self.root))
