"""Preserve exact proof identities without exempting them from secret handling."""
from __future__ import annotations
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import rls_validation_support as redaction
from tools import test_plan


class ReceiptIdentityTests(unittest.TestCase):
    ID = 'tests.fixture.Case.test_reuse_user_result'

    def receipt(self):
        return {'source_sha': 'a' * 40, 'success': True, 'tests_run': 1,
                'unique_tests': 1, 'executed_ids': [self.ID],
                'successful_ids': [self.ID], 'coverage': {'VFY': {'passed': 1}},
                'timings': [{'id': self.ID, 'seconds': 0.01}],
                'vfy_strict_observations': {'VFY-E001': {
                    'status': 'PASS', 'summary': 'The intended basic use is verified'}},
                'log': self.ID + ' ... ok\n'}

    def test_basic_prose_preserves_ids_and_observations(self):
        value = self.receipt()
        self.assertEqual(value, redaction.redact_value(value))
        self.assertEqual(value, test_plan.checked_suite_receipt(value, {self.ID: None}))

    def test_basic_prose_is_not_a_credential_in_any_casing(self):
        for phrase in ('basic use', 'Basic usage', 'BASIC TEST', 'Basic realm="demo"'):
            with self.subTest(phrase=phrase):
                self.assertEqual(phrase, redaction.redact_text(phrase))

    def test_actual_basic_credentials_remain_redacted(self):
        for pair in (b'user:pass', b':', 'user:密码'.encode(), b'name:pass:more'):
            for padded in (True, False):
                with self.subTest(pair=pair, padded=padded):
                    token = base64.b64encode(pair).decode()
                    if not padded:
                        token = token.rstrip('=')
                    safe = redaction.redact_value({'authorization_line': 'Basic ' + token,
                                                   'echo': token, 'summary': 'basic use'})
                    self.assertEqual('[REDACTED]', safe['authorization_line'])
                    self.assertEqual('[REDACTED]', safe['echo'])
                    self.assertEqual('basic use', safe['summary'])

    def test_explicit_malformed_auth_header_still_masks_its_payload(self):
        safe = redaction.redact_value({'log': 'Authorization: Basic use\n', 'echo': 'use'})
        self.assertNotIn('use', safe['log'])
        self.assertEqual('[REDACTED]', safe['echo'])

    def test_explicit_secret_fields_and_args_are_not_whitelisted(self):
        for value in ({'authorization': 'Basic use', 'echo': 'use'},
                      {'password': 'use', 'echo': 'use'},
                      {'argv': ['cli', '--authorization', 'Basic use'], 'echo': 'use'}):
            with self.subTest(value=value):
                self.assertEqual('[REDACTED]', redaction.redact_value(value)['echo'])

    def test_bearer_and_secret_propagation_are_unchanged(self):
        value = {'header': 'Bearer SYNTHETIC_DEMO_0123456789',
                 'echo': 'SYNTHETIC_DEMO_0123456789', 'purpose': 'basic use'}
        safe = redaction.redact_value(value)
        self.assertEqual('[REDACTED]', safe['echo'])
        self.assertEqual('basic use', safe['purpose'])

    def test_known_secret_overlapping_test_identity_fails_closed(self):
        value = self.receipt()
        with patch.dict(redaction.os.environ, {'AUDIT_PASSWORD': 'reuse'}):
            with self.assertRaisesRegex(ValueError, 'receipt identity changed'):
                test_plan.checked_suite_receipt(value, {self.ID: None})
        self.assertEqual(self.ID, value['executed_ids'][0])

    def test_missing_or_duplicate_execution_is_not_accepted(self):
        for ids in ([], [self.ID, self.ID], ['tests.some_other_test']):
            value = self.receipt(); value['executed_ids'] = ids
            with self.subTest(ids=ids), self.assertRaisesRegex(ValueError, 'exact source collection'):
                test_plan.checked_suite_receipt(value, {self.ID: None})

    def test_serialized_proof_tampering_is_rejected(self):
        value = self.receipt()
        for field, change in [('source_sha', 'b' * 40),
                              ('executed_ids', ['tests.changed']),
                              ('coverage', {}), ('vfy_strict_observations', {})]:
            altered = copy.deepcopy(value); altered[field] = change
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'receipt identity changed'):
                test_plan.require_receipt_identity(value, altered)

    def test_failed_suite_remains_a_failed_archivable_result(self):
        value = self.receipt();value.update(success=False, successful_ids=[], failures=1)
        safe = test_plan.checked_suite_receipt(value, {self.ID: None})
        self.assertFalse(safe['success']);self.assertEqual(1, safe['failures'])

    def test_first_persisted_receipt_preserves_proof_fields(self):
        value = self.receipt()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'suite.json'
            safe = test_plan.checked_suite_receipt(value, {self.ID: None})
            redaction.write_json(path, safe)
            persisted = json.loads(path.read_text())
            test_plan.require_receipt_identity(value, persisted)
            self.assertEqual(value, persisted)

    def test_tuple_arrays_preserve_json_proof_without_bypassing_value_checks(self):
        value = self.receipt()
        value['vfy_strict_observations']['VFY-E001']['returns'] = ('RET-001', 'RET-002')
        safe = test_plan.checked_suite_receipt(value, {self.ID: None})
        test_plan.require_receipt_identity(value, json.loads(json.dumps(safe)))
        safe['vfy_strict_observations']['VFY-E001']['returns'][0] = 'RET-999'
        with self.assertRaisesRegex(ValueError, 'vfy_strict_observations'):
            test_plan.require_receipt_identity(value, safe)

    def test_redaction_of_strict_observation_cannot_receive_pass(self):
        value = self.receipt();value['vfy_strict_observations']['VFY-E001']['token'] = 'dummy'
        with self.assertRaisesRegex(ValueError, 'vfy_strict_observations'):
            test_plan.checked_suite_receipt(value, {self.ID: None})


if __name__ == '__main__':
    unittest.main()
