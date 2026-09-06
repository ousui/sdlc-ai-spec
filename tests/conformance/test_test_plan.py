"""Protect the one-pass runner's accounting rather than repeating domain suites."""
from __future__ import annotations
import unittest
from unittest.mock import patch
from tools import test_plan
from tests.evals.late_phase_eval import test_registry


class TestPlanGuards(unittest.TestCase):
    def fixture(self, action):
        class Probe(unittest.TestCase):
            def runTest(inner):
                action(inner)
        return Probe()

    def run_probe(self, test, *, strict=False, maps=None):
        mapping = maps if maps is not None else {'IMP': {'IMP-PROBE': [test.id()]}, 'VFY': {}}
        with patch.object(test_plan, 'bindings', return_value=mapping):
            return test_plan.execute({test.id(): test}, strict=strict)

    def test_duplicate_ids_are_rejected_before_execution(self):
        item = self.fixture(lambda case: None)
        with self.assertRaisesRegex(ValueError, 'duplicate collected test'):
            test_registry(unittest.TestSuite([item, item]))

    def test_success_is_counted_once(self):
        calls = []
        item = self.fixture(lambda case: calls.append('actual'))
        result = self.run_probe(item)
        self.assertTrue(result['success'])
        self.assertEqual(['actual'], calls)
        self.assertEqual([item.id()], result['executed_ids'])
        self.assertEqual([item.id()], result['successful_ids'])
        self.assertEqual(1, result['coverage']['IMP']['passed'])
        self.assertEqual('PORTABLE_CONTRACT_TESTS_ONLY_NOT_STRICT_EVAL', result['coverage']['VFY']['status'])

    def test_failed_case_cannot_receive_coverage_credit(self):
        result = self.run_probe(self.fixture(lambda case: case.fail('deliberate rejection')))
        self.assertFalse(result['success'])
        self.assertEqual(1, result['failures'])
        self.assertEqual(0, result['coverage']['IMP']['passed'])

    def test_runtime_skip_fails_the_entire_result(self):
        result = self.run_probe(self.fixture(lambda case: case.skipTest('unavailable')))
        self.assertFalse(result['success'])
        self.assertEqual(1, result['skipped'])
        self.assertEqual(0, result['coverage']['IMP']['passed'])

    def test_expected_failure_cannot_be_reported_as_success(self):
        item = self.fixture(lambda case: case.fail('not implemented'))
        item.__class__.runTest = unittest.expectedFailure(item.__class__.runTest)
        result = self.run_probe(item)
        self.assertFalse(result['success'])
        self.assertEqual(1, result['expected_failures'])
        self.assertEqual(0, result['coverage']['IMP']['passed'])

    def test_strict_mode_requires_actual_observation_not_only_test_success(self):
        item = self.fixture(lambda case: None)
        result = self.run_probe(item, strict=True, maps={'VFY': {'VFY-E041': [item.id()]}})
        self.assertFalse(result['success'])
        self.assertEqual('MISSING_EXECUTION_EVIDENCE', result['coverage']['VFY']['status'])
        self.assertEqual({}, result['vfy_strict_observations'])
