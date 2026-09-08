"""Independent SCR oracles fixed from the original failures before implementation.

These reproduce the reported request-construction failures with controlled
fixtures, not a claim that the user's product worktree was executed.
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
        self.assertFalse(result['next_action']['requires_user'])
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


    def test_input_02_reports_both_environment_enums_without_echoing_raw_values(self):
        value = self.fixture.invocation(dry_run=True)
        value['inputs']['context']['environments'] = [{
            'id': 'ENV-001', 'environment': 'unrecognized-environment', 'purpose': 'API development',
            'accessibility': 'unrecognized-access', 'data_and_network_boundary': 'local only',
            'basis': 'observed', 'basis_references': ['EVD-002']}]
        result = self.assert_refused_without_artifact(value)
        paths = {e.get('details', {}).get('path') for e in result['errors']}
        self.assertIn('inputs.context.environments[0].environment', paths)
        self.assertIn('inputs.context.environments[0].accessibility', paths)
        self.assertNotIn('unrecognized-environment', json.dumps(result))

    def test_input_03_safe_purpose_aliases_are_recorded_without_mutating_input(self):
        for text in ('构建', 'bulid', 'buidl', ' BUILD '):
            with self.subTest(text=text):
                value = self.fixture.invocation(dry_run=True)
                value['inputs']['context']['engineering_entries'] = [{
                    'id': 'ENG-001', 'purpose': text, 'command_or_entry_point': 'mvn verify',
                    'working_scope': 'RSC-001', 'preconditions': 'JDK21',
                    'basis': 'observed', 'basis_references': ['EVD-002']}]
                original = deepcopy(value)
                result = self.fixture.invoke(value)
                self.assertTrue(result['ok'], result)
                normalized = [w for w in result['warnings'] if w['code'] == 'INPUT_NORMALIZED']
                self.assertEqual(1, len(normalized))
                self.assertEqual('build', normalized[0]['details']['canonical_value'])
                self.assertEqual(original, value)
                self.assertIsNone(result['artifact'])
                self.assertFalse((self.root / '.sdlc').exists())

    def test_input_04_dependency_prose_is_not_guessed_as_a_component_id(self):
        value = self.fixture.invocation(dry_run=True)
        value['inputs']['context']['components'] = [{
            'id': 'CMP-001', 'name': 'API', 'type': 'service', 'resource_reference': 'RSC-001',
            'responsibility': 'API', 'entry_point': 'main.py', 'depends_on': '依赖数据库服务',
            'authority_reference': 'EVD-001', 'basis': 'observed', 'basis_references': ['EVD-002']}]
        result = self.assert_refused_without_artifact(value)
        self.assertTrue(any(e.get('details', {}).get('path', '').endswith('.depends_on') for e in result['errors']))
        value['inputs']['context']['components'][0]['depends_on'] = 'None'
        self.assertTrue(self.fixture.invoke(value)['ok'])

    def test_input_05_evidence_digest_binds_supplied_member_bytes(self):
        value = self.fixture.invocation(dry_run=True)
        content = 'A retained fixture decision, not a real user authorization.\n'
        digest = 'sha256:' + hashlib.sha256(content.encode('utf-8')).hexdigest()
        value['inputs']['supporting_members'] = [{
            'member_id': 'SUP-001', 'canonical_name': 'decision.txt', 'media_type': 'text/plain',
            'purpose': 'test provenance', 'content': content}]
        value['inputs']['evidence'][0].update(reference='decision.txt', integrity_or_digest=digest)
        self.assertTrue(self.fixture.invoke(value)['ok'])
        value['inputs']['evidence'][0]['integrity_or_digest'] = 'sha256:' + '0' * 64
        self.assert_refused_without_artifact(value)
        value['inputs']['evidence'][0].update(reference='decision.txt@sha256:' + '0' * 64, integrity_or_digest=digest)
        self.assert_refused_without_artifact(value)

    def test_input_05_bad_digest_and_time_are_independent_diagnostics(self):
        value = self.fixture.invocation(dry_run=True)
        value['inputs']['evidence'][0].update(integrity_or_digest='不适用', produced_at='yesterday')
        result = self.assert_refused_without_artifact(value)
        paths = {e.get('details', {}).get('path') for e in result['errors']}
        self.assertIn('inputs.evidence[0].integrity_or_digest', paths)
        self.assertIn('inputs.evidence[0].produced_at', paths)

    def test_input_08_true_rejection_fails_only_final_confirmation_check(self):
        value = self.fixture.invocation(dry_run=True)
        # The authority verifier is isolated here: the oracle concerns only the
        # mapping of a verified rejection, not evidence authenticity.
        confirmation = {'result': 'rejected', 'mode': 'human', 'confirmer': 'reviewer',
                        'role': 'owner', 'authority_reference': 'authority.txt',
                        'accepted_exception_references': [], 'confirmed_at': '2026-09-08T00:00:00Z',
                        'control_input_digest': 'sha256:' + 'a' * 64,
                        'evaluation_contract_set': ctx.runtime.EVALUATION_CONTRACT_SET,
                        'check_set_result_digest': 'sha256:' + 'b' * 64}
        with patch.object(ctx.runtime, '_validate_final_confirmation', return_value=(confirmation, None)):
            product = ctx.runtime.build_payload(value, artifact_id='CTX-00000000000000-00',
                                                revision=1, base_revision=None, now=ctx.FIXED_TIME)
        self.assertEqual('fail', product.gate_result)
        self.assertEqual(['CORE-G-009'], product.failed_checks)
        self.assertTrue(product.errors)
        self.assertFalse((self.root / '.sdlc').exists())

    def test_input_13_bad_fact_basis_type_is_structured_not_a_typeerror(self):
        value = self.fixture.invocation(dry_run=True)
        value['inputs']['context']['project_identity']['purpose']['basis'] = []
        self.assert_refused_without_artifact(value)


    def test_input_14_old_frozen_baseline_is_not_rewritten_by_new_request_validation(self):
        historical_context = self.fixture.context()
        historical_context['resources'][0]['baseline_reference'] = 'workspace observation at 2026-08-30'
        # Reconstruct an old accepted Artifact using only the pre-fix baseline
        # predicate. The read-only verifier remains real and unpatched.
        with patch.object(self.fixture, 'context', return_value=historical_context), patch.object(ctx.runtime, '_immutable_baseline', return_value=True):
            reference, _ = self.fixture.create_and_freeze()
        before = snapshot(self.root)
        result = self.fixture.invoke(self.fixture.invocation('check', reference=reference))
        self.assertTrue(result['ok'], result)
        self.assertEqual('frozen', result['artifact']['revision_state'])
        self.assertEqual(before, snapshot(self.root))

    def test_input_13_non_string_evidence_identity_does_not_crash_before_preflight(self):
        value = self.fixture.invocation(dry_run=True)
        value['inputs']['evidence'].append({'id': []})
        self.assert_refused_without_artifact(value)


class MetaCommandRegressions(unittest.TestCase):
    def probe(self, phase, *, open_stdin):
        with tempfile.TemporaryDirectory(prefix='scr-meta-') as directory:
            root = Path(directory)
            script = ROOT / 'skills' / ('sdlc-' + phase) / 'scripts/runtime.py'
            for command in ('help', 'version', 'commands', 'examples', '--help', '-V'):
                with self.subTest(phase=phase, command=command, open_stdin=open_stdin):
                    with tempfile.TemporaryFile(mode="w+t") as out, tempfile.TemporaryFile(mode="w+t") as err:
                        process = subprocess.Popen([sys.executable, '-B', str(script), command, '--output', 'json'],
                                                   stdin=subprocess.PIPE, stdout=out, stderr=err,
                                                   cwd=root, text=True,
                                                   env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
                        try:
                            if not open_stdin:
                                process.stdin.write('{invalid business JSON')
                                process.stdin.close()
                                process.stdin = None
                            try:
                                process.wait(timeout=8)
                            except subprocess.TimeoutExpired:
                                self.fail('meta command consumed non-terminating business stdin')
                            out.seek(0); err.seek(0)
                            stdout, stderr = out.read(), err.read()
                            self.assertEqual(0, process.returncode, (stdout, stderr))
                            result = json.loads(stdout)
                            self.assertTrue(result['ok'], result)
                            self.assertEqual('meta', result['state'])
                            self.assertEqual([], result['effects'])
                            self.assertEqual([], list(root.iterdir()))
                        finally:
                            if process.poll() is None:
                                process.kill()
                            if process.stdin is not None:
                                process.stdin.close()
                            process.wait(timeout=5)

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



class RelatedInputRegressions(unittest.TestCase):
    def test_input_09_req_invalid_enum_rejected_before_store_even_with_write_authorization(self):
        from tests.skill_req.support import runtime as req
        with tempfile.TemporaryDirectory(prefix='scr-req-') as directory:
            root = Path(directory)
            handler = req.RequirementHandler(root)
            for operation in ('create', 'revise'):
                for dry in (False, True):
                    with self.subTest(operation=operation, dry=dry):
                        value = {'operation': operation, 'project_root': directory,
                                 'inputs': {'requirement': {'sources': [{'type': 'chatty'}],
                                                           'requirements': [{'type': []}]}},
                                 'options': {'dry_run': dry}, 'confirmations': [{'type': 'write', 'approved': True}]}
                        with patch.object(req.base.ArtifactStore, 'open_read_only', side_effect=AssertionError('unexpected read')), \
                             patch.object(req.base.ArtifactStore, 'open_read_write', side_effect=AssertionError('unexpected write')):
                            result = getattr(handler, operation)(value)
                        self.assertFalse(result['ok'])
                        self.assertEqual({'result': 'pending', 'failed_checks': []}, result['gate'])
                        self.assertIsNone(result['artifact'])
                        self.assertEqual(2, len(result['errors'][0]['details']))
                        self.assertEqual([], list(root.iterdir()))

    def test_input_09_req_missing_facts_in_an_object_are_not_structural_errors(self):
        from tests.skill_req.support import runtime as req
        with tempfile.TemporaryDirectory(prefix='scr-req-') as directory:
            handler = req.RequirementHandler(Path(directory))
            self.assertIsNone(handler._input_preflight({'operation': 'create', 'inputs': {'requirement': {}}}))
            for value in ([], 'description', True):
                result = handler._input_preflight({'operation': 'create', 'inputs': {'requirement': value}})
                self.assertEqual('REQ_CONTENT_INVALID', result['errors'][0]['code'])

    def test_input_13_truthy_strings_cannot_enable_vfy_or_rls_operations(self):
        for phase, fields in (('500-vfy', ('persist', 'run_automated', 'allow_commands', 'finalize')),
                              ('600-rls', ('force_fail', 'pipeline_only', 'retry', 'write_confirmed'))):
            with tempfile.TemporaryDirectory(prefix='scr-bool-') as directory:
                for field in fields:
                    with self.subTest(phase=phase, field=field):
                        output = subprocess.run([sys.executable, '-B', str(ROOT/'skills'/('sdlc-'+phase)/'scripts/runtime.py'),
                                                 'create', '--output', 'json'], input=json.dumps({field: 'false'}),
                                                text=True, capture_output=True, cwd=directory, timeout=12)
                        self.assertEqual(2, output.returncode, output.stdout + output.stderr)
                        result = json.loads(output.stdout)
                        self.assertFalse(result['ok'])
                        self.assertIn(field, json.dumps(result['errors']))
                        self.assertIn('boolean', json.dumps(result['errors']))
                        self.assertEqual([], list(Path(directory).iterdir()))
